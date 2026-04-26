"""
Brand ingestion pipeline.

Scrapes a website → extracts multimodal brand identity via LLM → stores in HydraDB.
"""
from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel

from agent.router import route, RouteType
from memory.brand_memory import BrandMemory


# ── Pydantic schema for structured LLM output ─────────────────────────────────

class BrandProfile(BaseModel):
    brand_name: str
    tagline: str
    formality: float          # 1–10 (1=casual, 10=formal)
    technical_depth: float    # 1–10
    humor: float              # 1–10
    sentence_style: str       # e.g. "short active voice"
    signature_phrases: list[str]
    taboo_words: list[str]    # words the brand never uses
    icp: str                  # ideal customer profile
    tone_summary: str         # 2-sentence brand voice description
    audio_energy: float       # 1–10 (1=calm, 10=high energy)
    audio_pace: str           # "slow" | "moderate" | "fast"


# ── LLM client ────────────────────────────────────────────────────────────────


def _scrape(url: str) -> str:
    """Fetch and clean website text. Returns up to 4000 chars."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BrandMind/1.0)"}
    resp = httpx.get(url, headers=headers, timeout=20, follow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    # Remove noise
    for tag in soup(["script", "style", "nav", "footer", "head"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()
    return text[:6000]


def _extract_profile(website_text: str, url: str) -> BrandProfile:
    """Use LLM to extract structured brand voice profile from website text."""
    prompt = f"""Analyze this website content and extract the brand's voice profile.
Be precise and specific — base everything on actual evidence from the text.

Website URL: {url}
Content:
{website_text}

Return a JSON object matching this exact schema:
- brand_name: string
- tagline: string (their actual tagline or a 1-sentence summary)
- formality: float 1-10 (1=very casual, 10=very formal)
- technical_depth: float 1-10
- humor: float 1-10
- sentence_style: string (describe their sentence patterns)
- signature_phrases: list of 3-5 actual phrases they use
- taboo_words: list of 3-5 words/phrases they clearly avoid
- icp: string (who they're talking to, 1 sentence)
- tone_summary: string (2 sentences describing their brand voice)
- audio_energy: float 1-10 (how energetic their voice would sound)
- audio_pace: "slow" | "moderate" | "fast"

Respond with ONLY the JSON object, no markdown."""

    import json
    data = route(RouteType.EXTRACTION, [{"role": "user", "content": prompt}], json_mode=True, temperature=0.2)
    return BrandProfile(**json.loads(data))


def ingest_brand(url: str, brand_id: str | None = None) -> tuple[BrandProfile, BrandMemory]:
    """
    Full ingestion pipeline:
    1. Scrape website
    2. Extract brand profile via LLM
    3. Store in HydraDB
    4. Return (profile, memory) for immediate use

    brand_id defaults to the domain name.
    """
    # Derive brand_id from domain if not provided
    if not brand_id:
        brand_id = re.sub(r"https?://(www\.)?", "", url).split("/")[0].replace(".", "_")

    print(f"  → Scraping {url}...")
    text = _scrape(url)

    print(f"  → Extracting brand profile via LLM...")
    profile = _extract_profile(text, url)

    print(f"  → Storing in HydraDB (tenant: brandmind / {brand_id})...")
    memory = BrandMemory(brand_id)
    memory.store_profile(profile.model_dump())
    memory.store(f"Website URL: {url}")
    memory.store(f"Brand voice summary: {profile.tone_summary}")

    return profile, memory


def sanitize_brand_id(brand_id: str) -> str:
    """Normalize brand_id to safe slug format."""
    import re
    return re.sub(r"[^a-z0-9_]", "_", brand_id.lower())[:40]
