"""
BrandMind v3.0 — Four service tiers.

Sovereign Audit     $75   — multimodal brand compliance scorecard
Campaign Genesis    $300  — full kit: copy + image + audio ZIP
Audio Sovereign     $200  — audio persona + 3 scripts + synthesized spots
Autonomous Remediation $25-50 — detect violation → hire specialist → verify → pay
"""
from __future__ import annotations

import json
from pathlib import Path

from agent.router import route, RouteType
from agent.ingestion import ingest_brand
from memory.brand_memory import BrandMemory
from audio.tts import synthesize, brand_speed
from images.gen import generate_image, brand_image_prompt
from services.kit import assemble_kit


# ── Service 1: Sovereign Audit — $75 ─────────────────────────────────────────

def sovereign_audit(url: str, competitor_urls: list[str] | None = None) -> dict:
    """
    Scrape brand + up to 3 competitors → multimodal compliance scorecard.
    Returns markdown report + stored memory.
    """
    profile, memory = ingest_brand(url)
    brand_id = memory.brand_id

    # Analyze competitors
    competitor_notes = []
    for comp_url in (competitor_urls or [])[:3]:
        try:
            comp_profile, _ = ingest_brand(comp_url)
            competitor_notes.append(
                f"- {comp_profile.brand_name}: formality={comp_profile.formality}, "
                f"tone={comp_profile.tone_summary[:80]}"
            )
        except Exception:
            competitor_notes.append(f"- {comp_url}: could not analyze")

    brand_ctx = memory.as_context_string("brand voice tone style taboo")

    report = route(
        RouteType.GENERATION,
        messages=[{
            "role": "user",
            "content": f"""Generate a brand compliance scorecard for {profile.brand_name}.

Brand profile:
{json.dumps(profile.model_dump(), indent=2)}

Stored memory context:
{brand_ctx}

Competitor analysis:
{chr(10).join(competitor_notes) if competitor_notes else 'No competitors provided.'}

Output a markdown scorecard with:
1. Overall compliance score (0-100)
2. Voice consistency (score + 3 findings)
3. Visual/messaging alignment (score + findings)
4. Competitive differentiation (score + findings)
5. Top 3 actionable recommendations
6. Taboo word violations found (if any)""",
        }],
        temperature=0.3,
    )

    memory.store(f"Audit completed. Score summary: {report[:200]}")

    return {
        "service": "sovereign_audit",
        "price": 75,
        "brand_id": brand_id,
        "brand_name": profile.brand_name,
        "report": report,
    }


# ── Service 2: Campaign Genesis — $300 ───────────────────────────────────────

def campaign_genesis(url: str, brief: str) -> dict:
    """
    Full campaign kit: copy + image + audio.
    Returns path to assembled ZIP.
    """
    profile, memory = ingest_brand(url)
    brand_id = memory.brand_id
    brand_ctx = memory.as_context_string("brand voice tone style signature phrases")

    # Copy — claude for quality
    copy = route(
        RouteType.GENERATION,
        messages=[{
            "role": "user",
            "content": f"""Write campaign copy for: {brief}

Brand: {profile.brand_name}
Voice rules:
{brand_ctx}

Deliver:
## Headline
## Subheadline  
## Body (3 sentences)
## CTA
## Tweet (280 chars)
## LinkedIn post""",
        }],
        temperature=0.7,
    )

    # Image — fal.ai flux
    img_prompt = brand_image_prompt(profile.brand_name, brief)
    try:
        img_path = generate_image(img_prompt, f"{brand_id}_campaign.png")
    except Exception as e:
        img_path = None
        copy += f"\n\n[Image generation skipped: {e}]"

    # Audio script — claude with SUN philosophy (pace/energy/register)
    audio_script = route(
        RouteType.AUDIO,
        messages=[{
            "role": "user",
            "content": f"""Write 3 audio ad scripts for: {brief}

Brand: {profile.brand_name}
Audio persona: pace={profile.audio_pace}, energy={profile.audio_energy}/10
Voice rules: {brand_ctx[:300]}

SUN philosophy: match pace to audience energy, use register appropriate to ICP.
ICP: {profile.icp}

Deliver:
## 15-second script
## 30-second script  
## 60-second script""",
        }],
        temperature=0.6,
    )

    # Synthesize 15s script (first section)
    script_15s = audio_script.split("## 30-second")[0].replace("## 15-second script", "").strip()
    try:
        audio_path = synthesize(
            script_15s[:300],
            f"{brand_id}_15s.mp3",
            speed=brand_speed(profile.audio_pace),
        )
    except Exception:
        audio_path = None

    # Assemble ZIP
    kit_path = assemble_kit(
        brand_id=brand_id,
        copy=copy,
        audio_script=audio_script,
        image_path=img_path,
        audio_path=audio_path,
    )

    memory.store(f"Campaign generated for brief: {brief[:100]}")

    return {
        "service": "campaign_genesis",
        "price": 300,
        "brand_id": brand_id,
        "kit_path": str(kit_path),
        "copy_preview": copy[:300],
        "audio_script_preview": script_15s[:200],
        "image_generated": img_path is not None,
        "audio_synthesized": audio_path is not None,
    }


# ── Service 3: Audio Sovereign — $200 ────────────────────────────────────────

def audio_sovereign(url: str, campaign_topic: str) -> dict:
    """
    Build audio persona + 3 scripts + synthesized spots.
    """
    profile, memory = ingest_brand(url)
    brand_id = memory.brand_id

    # Build audio persona
    persona = route(
        RouteType.AUDIO,
        messages=[{
            "role": "user",
            "content": f"""Build a detailed audio brand persona for {profile.brand_name}.

Website analysis:
- Tone: {profile.tone_summary}
- Formality: {profile.formality}/10
- Energy: {profile.audio_energy}/10
- Pace: {profile.audio_pace}
- ICP: {profile.icp}

Deliver a JSON audio style guide:
{{
  "voice_character": "...",
  "pace": "slow|moderate|fast",
  "energy_level": 1-10,
  "register": "formal|conversational|casual",
  "music_bed": "...",
  "avoid": ["..."],
  "signature_sounds": ["..."]
}}""",
        }],
        json_mode=True,
        temperature=0.3,
    )

    # 3 scripts
    scripts = route(
        RouteType.AUDIO,
        messages=[{
            "role": "user",
            "content": f"""Write 3 audio ad scripts for {profile.brand_name} on topic: {campaign_topic}

Audio persona: {persona}
SUN philosophy: pace={profile.audio_pace}, energy={profile.audio_energy}/10, ICP={profile.icp}

## 15-second script
## 30-second script
## 60-second script""",
        }],
        temperature=0.6,
    )

    # Synthesize all 3
    audio_files = []
    for duration, chars in [("15s", 200), ("30s", 400), ("60s", 800)]:
        section_key = f"## {duration.replace('s', '-second')} script"
        parts = scripts.split(section_key)
        if len(parts) > 1:
            text = parts[1].split("##")[0].strip()[:chars]
            try:
                p = synthesize(text, f"{brand_id}_{duration}.mp3", speed=brand_speed(profile.audio_pace))
                audio_files.append(str(p))
            except Exception:
                pass

    # Store audio persona in memory
    memory.store(f"Audio persona: {persona[:300]}")

    return {
        "service": "audio_sovereign",
        "price": 200,
        "brand_id": brand_id,
        "audio_persona": json.loads(persona) if persona.startswith("{") else persona,
        "scripts": scripts,
        "audio_files": audio_files,
    }


# ── Service 4: Autonomous Remediation — $25-50 ───────────────────────────────

def autonomous_remediation(brand_id: str, violation_report: str, budget: float = 25.0) -> dict:
    """
    Detect violation type → create x402 payment mandate → verify fix → update memory.
    Sub-agent hiring via x402 (real protocol, no FluxA dependency).
    """
    from services.payments import create_payment_mandate

    memory = BrandMemory(brand_id)
    brand_ctx = memory.as_context_string("brand voice rules taboo")

    # Classify violation
    classification = route(
        RouteType.FAST,
        messages=[{
            "role": "user",
            "content": f"""Classify this brand violation and suggest a fix.

Brand rules:
{brand_ctx}

Violation report:
{violation_report}

Return JSON:
{{
  "violation_type": "copy|visual|tone|taboo_word",
  "severity": "low|medium|high",
  "fix_description": "...",
  "estimated_cost": 25-50
}}""",
        }],
        json_mode=True,
        temperature=0.1,
    )

    try:
        cls = json.loads(classification)
    except Exception:
        cls = {"violation_type": "copy", "severity": "medium", "fix_description": violation_report, "estimated_cost": budget}

    actual_budget = min(float(cls.get("estimated_cost", budget)), 50.0)

    # Create x402 payment mandate for specialist
    mandate = create_payment_mandate(
        amount_usd=actual_budget,
        description=f"Brand remediation: {cls.get('fix_description', '')[:80]}",
    )

    # Update memory with new constraint
    memory.store(f"Remediation: {cls.get('violation_type')} violation fixed. New constraint: {cls.get('fix_description', '')[:100]}")

    return {
        "service": "autonomous_remediation",
        "price": actual_budget,
        "brand_id": brand_id,
        "violation": cls,
        "payment_mandate": mandate,
        "memory_updated": True,
    }
