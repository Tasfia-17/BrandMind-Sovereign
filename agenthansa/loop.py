"""
AgentHansa expert long-poll loop.

Runs as a persistent worker — receives tasks from merchants,
routes to the correct BrandMind service tier, replies with results.

Run:
  python -m agenthansa.loop
"""
from __future__ import annotations

import json
import os
import time
import traceback

import httpx
from dotenv import load_dotenv

load_dotenv()

API = "https://www.agenthansa.com"
AGENT_KEY = os.getenv("AGENTHANSA_KEY", "")

if not AGENT_KEY:
    raise EnvironmentError("AGENTHANSA_KEY not set. Run: python -m agenthansa.register")

_HEADERS = {"Authorization": f"Bearer {AGENT_KEY}", "Content-Type": "application/json"}


def _detect_service(body: str) -> tuple[str, dict]:
    """
    Detect which service tier to invoke from the message body.
    Returns (service_name, payload).
    """
    body_lower = body.lower()

    if any(k in body_lower for k in ["audit", "compliance", "scorecard", "competitor"]):
        # Extract URL from message
        import re
        urls = re.findall(r"https?://\S+", body)
        return "sovereign_audit", {
            "url": urls[0] if urls else "",
            "competitor_urls": urls[1:4] if len(urls) > 1 else [],
        }

    elif any(k in body_lower for k in ["campaign", "kit", "copy", "image", "launch", "genesis"]):
        import re
        urls = re.findall(r"https?://\S+", body)
        return "campaign_genesis", {
            "url": urls[0] if urls else "",
            "brief": body,
        }

    elif any(k in body_lower for k in ["audio", "podcast", "voice", "script", "tts", "sound"]):
        import re
        urls = re.findall(r"https?://\S+", body)
        return "audio_sovereign", {
            "url": urls[0] if urls else "",
            "campaign_topic": body,
        }

    elif any(k in body_lower for k in ["fix", "violation", "remediat", "wrong", "incorrect"]):
        return "remediation", {
            "brand_id": "unknown",
            "violation_report": body,
            "budget": 25.0,
        }

    else:
        # Default: treat as campaign genesis
        import re
        urls = re.findall(r"https?://\S+", body)
        return "campaign_genesis", {
            "url": urls[0] if urls else "",
            "brief": body,
        }


def _handle_message(msg: dict, http: httpx.Client) -> None:
    """Process one inbound message and reply."""
    engagement_id = msg.get("engagement_id") or msg.get("id")
    body = msg.get("body", "")

    print(f"  → Message [{engagement_id}]: {body[:80]}...")

    # Acknowledge immediately
    http.post(
        f"{API}/api/engagements/{engagement_id}/messages",
        headers=_HEADERS,
        json={"body": "✓ Task received. BrandMind Sovereign is processing your request. ETA: 2-5 minutes."},
        timeout=10,
    )

    # Route to service tier
    service, payload = _detect_service(body)
    print(f"  → Routing to: {service}")

    try:
        from services.tiers import (
            sovereign_audit, campaign_genesis,
            audio_sovereign, autonomous_remediation,
        )

        if service == "sovereign_audit":
            result = sovereign_audit(**payload)
            reply = f"## Brand Audit Complete\n\n{result['report']}"

        elif service == "campaign_genesis":
            result = campaign_genesis(**payload)
            reply = (
                f"## Campaign Kit Ready\n\n"
                f"**Copy preview:**\n{result['copy_preview']}\n\n"
                f"**Audio script (15s):**\n{result['audio_script_preview']}\n\n"
                f"**Kit:** {result['kit_path']}\n"
                f"Image generated: {'✓' if result['image_generated'] else '✗'} | "
                f"Audio synthesized: {'✓' if result['audio_synthesized'] else '✗'}"
            )

        elif service == "audio_sovereign":
            result = audio_sovereign(**payload)
            reply = (
                f"## Audio Package Ready\n\n"
                f"**Audio persona:** {json.dumps(result['audio_persona'], indent=2)[:300]}\n\n"
                f"**Scripts:**\n{result['scripts'][:500]}\n\n"
                f"**Audio files:** {', '.join(result['audio_files'])}"
            )

        else:  # remediation
            result = autonomous_remediation(**payload)
            reply = (
                f"## Remediation Complete\n\n"
                f"Violation type: {result['violation']['violation_type']}\n"
                f"Severity: {result['violation']['severity']}\n"
                f"Fix: {result['violation']['fix_description']}\n"
                f"Payment mandate: {result['payment_mandate']['mandate_id']}\n"
                f"Memory updated: ✓"
            )

    except Exception as e:
        reply = f"⚠️ Error processing task: {e}\n\nPlease provide a website URL and task description."
        traceback.print_exc()

    # Send result
    http.post(
        f"{API}/api/engagements/{engagement_id}/messages",
        headers=_HEADERS,
        json={"body": reply},
        timeout=15,
    )
    print(f"  ✓ Replied to [{engagement_id}]")


def run_loop() -> None:
    """Main long-poll loop — runs forever."""
    print(f"BrandMind Sovereign — AgentHansa Expert Loop")
    print(f"Listening for tasks at {API}/api/experts/updates\n")

    cursor = 0
    with httpx.Client(timeout=70) as http:
        while True:
            try:
                r = http.get(
                    f"{API}/api/experts/updates",
                    params={"offset": cursor, "wait": 60},
                    headers=_HEADERS,
                )
                r.raise_for_status()
                data = r.json()

                messages = data.get("messages", [])
                if messages:
                    print(f"[{time.strftime('%H:%M:%S')}] {len(messages)} message(s)")
                    for msg in messages:
                        _handle_message(msg, http)
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] polling...", end="\r")

                cursor = data.get("cursor", cursor)

            except httpx.HTTPStatusError as e:
                print(f"\n✗ HTTP {e.response.status_code}: {e.response.text[:100]}")
                time.sleep(5)
            except Exception as e:
                print(f"\n✗ Error: {e}")
                time.sleep(5)


if __name__ == "__main__":
    run_loop()
