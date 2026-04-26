"""
Fish Audio TTS layer.

Synthesizes brand copy into audio using the brand's voice persona.
Pace and energy are derived from the brand profile stored in HydraDB.
"""
from __future__ import annotations

from pathlib import Path

from fishaudio import FishAudio, save
from fishaudio.types import TTSConfig, Prosody

from agent.config import FISH_API_KEY, FISH_VOICE_ID

_client = FishAudio(api_key=FISH_API_KEY)

OUTPUT_DIR = Path(__file__).parent.parent / "demo" / "audio"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def synthesize(
    text: str,
    filename: str,
    speed: float = 1.0,
    volume: float = 0.0,
    voice_id: str | None = None,
) -> Path:
    """
    Synthesize text to audio file.

    speed: 0.5–2.0 (1.0 = normal)
    volume: dB adjustment (-20 to +20)
    voice_id: Fish Audio voice ID (uses FISH_VOICE_ID env var if not provided)
    """
    ref_id = voice_id or FISH_VOICE_ID or None

    config = TTSConfig(
        prosody=Prosody(speed=speed, volume=volume),
        format="mp3",
        streaming=False,
        latency="balanced",
        **({"reference_id": ref_id} if ref_id else {}),
    )

    audio = _client.tts.convert(text=text, config=config)
    out_path = OUTPUT_DIR / filename
    save(audio, str(out_path))
    return out_path


def brand_speed(audio_pace: str) -> float:
    """Map brand audio pace to Fish Audio speed multiplier."""
    return {"slow": 0.85, "moderate": 1.0, "fast": 1.2}.get(audio_pace, 1.0)
