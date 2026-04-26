"""
Image generation via fal.ai flux-schnell.
~$0.003/image, ~0.5s latency.
"""
from __future__ import annotations

import os
import httpx
from pathlib import Path

FAL_KEY = os.getenv("FAL_API_KEY", "")
_API = "https://fal.run/fal-ai/flux/schnell"

OUTPUT_DIR = Path(__file__).parent.parent / "demo" / "images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_image(prompt: str, filename: str, size: str = "landscape_4_3") -> Path:
    """
    Generate an image via fal.ai flux-schnell.
    Returns local path to saved PNG.
    """
    if not FAL_KEY:
        raise EnvironmentError("FAL_API_KEY not set. Get key at fal.ai/dashboard")

    resp = httpx.post(
        _API,
        headers={"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"},
        json={"prompt": prompt, "image_size": size, "num_images": 1},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    image_url = data["images"][0]["url"]

    # Download and save
    img_bytes = httpx.get(image_url, timeout=30).content
    out_path = OUTPUT_DIR / filename
    out_path.write_bytes(img_bytes)
    return out_path


def brand_image_prompt(brand_name: str, campaign_topic: str, palette: str = "") -> str:
    """Build a flux prompt from brand context."""
    palette_hint = f", color palette: {palette}" if palette else ""
    return (
        f"Professional marketing visual for {brand_name}, {campaign_topic}"
        f"{palette_hint}, clean modern design, no text, high quality"
    )
