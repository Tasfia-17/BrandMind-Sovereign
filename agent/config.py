"""Central config — loads .env and validates required keys."""
import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val or "placeholder" in val or val.endswith("_here"):
        raise EnvironmentError(f"Missing {key}. See .env")
    return val


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


# ── Required ──────────────────────────────────────────────────────────────────
FISH_API_KEY: str = _require("FISH_API_KEY")
FAL_API_KEY: str = _require("FAL_API_KEY")
TOKENROUTER_API_KEY: str = _require("TOKENROUTER_API_KEY")
TOKENROUTER_BASE_URL: str = _optional("TOKENROUTER_BASE_URL", "https://api.tokenrouter.com/v1")

# ── Optional (set after registration steps) ───────────────────────────────────
BOTLEARN_API_KEY: str = _optional("BOTLEARN_API_KEY")
AGENTHANSA_KEY: str = _optional("AGENTHANSA_KEY")
FLUXA_OAUTH_ID: str = _optional("FLUXA_OAUTH_ID")
FLUXA_OAUTH_TOKEN: str = _optional("FLUXA_OAUTH_TOKEN")
FLUXA_AGENT_ID: str = _optional("FLUXA_AGENT_ID")
EVM_WALLET_ADDRESS: str = _optional("EVM_WALLET_ADDRESS")
FISH_VOICE_ID: str = _optional("FISH_VOICE_ID")
HYDRADB_API_KEY: str = _optional("HYDRADB_API_KEY")

# Legacy alias
LLM_MODEL = "anthropic/claude-sonnet-4-5"
