"""
AgentHansa registration script.

Run once to register BrandMind as a hireable expert:
  python -m agenthansa.register

Steps:
  1. Register agent identity → get tabb_ API key
  2. Wire FluxA wallet (or x402 fallback)
  3. Upgrade to expert
  4. Declare 4 service tiers
"""
from __future__ import annotations

import json
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

API = "https://www.agenthansa.com"
AGENT_KEY = os.getenv("AGENTHANSA_KEY", "")
FLUXA_AGENT_ID = os.getenv("FLUXA_AGENT_ID", "")
FLUXA_OAUTH_ID = os.getenv("FLUXA_OAUTH_ID", "")
FLUXA_OAUTH_TOKEN = os.getenv("FLUXA_OAUTH_TOKEN", "")
EVM_WALLET = os.getenv("EVM_WALLET_ADDRESS", "")


def _headers() -> dict:
    return {"Authorization": f"Bearer {AGENT_KEY}", "Content-Type": "application/json"}


def register_agent() -> str:
    """Step 1: Register agent, returns tabb_ API key."""
    resp = httpx.post(
        f"{API}/api/agents/register",
        headers={"Content-Type": "application/json"},
        json={
            "name": "BrandMind Sovereign",
            "description": (
                "Autonomous multimodal brand voice agent. "
                "Audits brand compliance, generates campaign kits (copy+image+audio), "
                "builds audio personas, and remediates brand violations. "
                "Powered by Hermes Agent + Mem0 + TokenRouter."
            ),
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    key = data.get("api_key", "")
    print(f"✓ Registered. API key: {key}")
    print("  ⚠️  Save this key — it's only shown once. Add to .env as AGENTHANSA_KEY")
    return key


def wire_wallet() -> None:
    """Step 2: Wire FluxA wallet using OAuth ID."""
    # Use OAuth ID as the fluxa_agent_id (that's what the MCP skill provides)
    fluxa_id = FLUXA_AGENT_ID or FLUXA_OAUTH_ID or EVM_WALLET
    if not fluxa_id:
        print("⚠️  No wallet configured. Skipping.")
        return

    resp = httpx.put(
        f"{API}/api/agents/fluxa-wallet",
        headers=_headers(),
        json={"fluxa_agent_id": fluxa_id},
        timeout=15,
    )
    resp.raise_for_status()
    print(f"✓ Wallet wired: {fluxa_id[:20]}...")


def upgrade_to_expert() -> None:
    """Step 3: Upgrade agent to expert status."""
    resp = httpx.post(
        f"{API}/api/experts/upgrade",
        headers=_headers(),
        json={
            "slug": "brandmind-sovereign",
            "display_name": "BrandMind Sovereign",
            "contact_email": os.getenv("CONTACT_EMAIL", "brandmind@example.com"),
            "bio": (
                "BrandMind Sovereign is an autonomous brand voice agent that audits, "
                "generates, and enforces brand identity at scale. "
                "Delivers campaign kits (copy + images + audio) in under 2 hours. "
                "Built on Hermes Agent + Mem0 persistent memory + TokenRouter multimodal inference."
            ),
            "specialties": ["brand-voice", "content-generation", "audio-production", "brand-audit"],
            "registration_notes": (
                "Accepts tasks via AgentHansa long-poll. "
                "Payments via FluxA AEP2 / x402. "
                "Memory persists across sessions via Mem0 + HydraDB."
            ),
        },
        timeout=15,
    )
    resp.raise_for_status()
    print(f"✓ Expert upgrade submitted. Status: pending (admin review)")
    print(f"  Profile: {API}/experts/brandmind-sovereign")


def declare_services() -> None:
    """Step 4: Declare all 4 service tiers."""
    services = [
        {
            "name": "Sovereign Audit",
            "description": (
                "Multimodal brand compliance scorecard. "
                "Scrapes your site + up to 3 competitors, analyzes voice/visual/messaging consistency, "
                "returns a scored markdown report with actionable fixes."
            ),
            "tiers": [
                {
                    "name": "Standard",
                    "price_usd": 75,
                    "sla_days": 1,
                    "deliverable_spec": "Markdown scorecard: overall score, 3 dimension scores, top 3 recommendations",
                }
            ],
        },
        {
            "name": "Campaign Genesis",
            "description": (
                "Full campaign kit: copy + image + audio. "
                "Generates headlines, body, CTA, social posts, hero image (flux-schnell), "
                "and 15s/30s/60s audio scripts synthesized via Fish Audio. Delivered as ZIP."
            ),
            "tiers": [
                {
                    "name": "Standard",
                    "price_usd": 300,
                    "sla_days": 1,
                    "deliverable_spec": "ZIP: copy.md + audio_scripts.md + hero image PNG + 15s MP3",
                }
            ],
        },
        {
            "name": "Audio Sovereign",
            "description": (
                "Audio brand persona + synthesized ad spots. "
                "Analyzes existing audio assets, builds audio persona (pace/energy/register), "
                "generates 3 scripts, synthesizes via Fish Audio TTS."
            ),
            "tiers": [
                {
                    "name": "Standard",
                    "price_usd": 200,
                    "sla_days": 1,
                    "deliverable_spec": "Audio style guide JSON + 3 scripts + 3 MP3 files (15s/30s/60s)",
                }
            ],
        },
        {
            "name": "Autonomous Remediation",
            "description": (
                "Detect brand violation → classify → create payment mandate → verify fix → update memory. "
                "Provide a violation report and approve mandate; agent handles the rest."
            ),
            "tiers": [
                {
                    "name": "Minor Fix",
                    "price_usd": 25,
                    "sla_days": 1,
                    "deliverable_spec": "Corrected asset + updated brand memory + violation report",
                },
                {
                    "name": "Major Fix",
                    "price_usd": 50,
                    "sla_days": 2,
                    "deliverable_spec": "Corrected asset + updated brand memory + full audit trail",
                },
            ],
        },
    ]

    for svc in services:
        resp = httpx.post(
            f"{API}/api/experts/me/services",
            headers=_headers(),
            json=svc,
            timeout=15,
        )
        resp.raise_for_status()
        tiers = [f"${t['price_usd']}" for t in svc["tiers"]]
        print(f"✓ Service declared: {svc['name']} ({'/'.join(tiers)})")


def main() -> None:
    global AGENT_KEY

    print("=== BrandMind Sovereign — AgentHansa Registration ===\n")

    if not AGENT_KEY or "placeholder" in AGENT_KEY:
        print("Step 1: Registering agent...")
        AGENT_KEY = register_agent()
        if not AGENT_KEY:
            print("✗ Registration failed — no API key returned")
            sys.exit(1)
        # Persist to .env
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        with open(env_path, "r") as f:
            content = f.read()
        content = content.replace("tabb_placeholder_set_after_register", AGENT_KEY)
        with open(env_path, "w") as f:
            f.write(content)
        print(f"  ✓ Saved to .env")
    else:
        print(f"Step 1: Using existing key: {AGENT_KEY[:16]}...")

    print("\nStep 2: Wiring wallet...")
    wire_wallet()

    print("\nStep 3: Upgrading to expert...")
    upgrade_to_expert()

    print("\nStep 4: Declaring services...")
    declare_services()

    print(f"""
=== Done ===

Add to your .env:
  AGENTHANSA_KEY={AGENT_KEY}

Start the expert loop:
  python -m agenthansa.loop

AgentHansa profile (once approved):
  {API}/experts/brandmind-sovereign

Submission form:
  {API}/hackathon-submit.html
""")


if __name__ == "__main__":
    main()
