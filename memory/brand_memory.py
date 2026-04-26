"""
Mem0 memory layer.

Stores and retrieves brand voice profiles across sessions using Mem0.
Uses TokenRouter as the LLM + embedder backend — one API key, no extra signup.
Local Qdrant vector store — no external DB needed.

Mem0 gives us:
- Vector search (semantic similarity)
- Automatic fact extraction from conversation pairs
- Cross-session persistence (SQLite + Qdrant on disk)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from mem0 import Memory

from agent.config import TOKENROUTER_API_KEY, TOKENROUTER_BASE_URL

_STORE_DIR = Path(__file__).parent.parent / ".mem0_store"
_STORE_DIR.mkdir(exist_ok=True)

_MEM0_CONFIG = {
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-4o-mini",
            "api_key": TOKENROUTER_API_KEY,
            "openai_base_url": TOKENROUTER_BASE_URL,
        },
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small",
            "api_key": TOKENROUTER_API_KEY,
            "openai_base_url": TOKENROUTER_BASE_URL,
        },
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "brandmind",
            "path": str(_STORE_DIR / "qdrant"),
        },
    },
    "history_db_path": str(_STORE_DIR / "history.db"),
}


class BrandMemory:
    """Persistent cross-session memory for a single brand using Mem0."""

    def __init__(self, brand_id: str) -> None:
        self.brand_id = brand_id
        self._mem = Memory.from_config(_MEM0_CONFIG)

    # ── Write ─────────────────────────────────────────────────────────────────

    def store(self, text: str) -> None:
        """Store a brand fact. Mem0 auto-extracts entities and relationships."""
        self._mem.add(text, user_id=self.brand_id)

    def store_profile(self, profile: dict[str, Any]) -> None:
        """Store the full brand profile. Each key fact stored individually."""
        import json
        # Store as conversation pair so Mem0 extracts structured facts
        self._mem.add(
            [
                {"role": "user", "content": "What is this brand's voice profile?"},
                {"role": "assistant", "content": json.dumps(profile, indent=2)},
            ],
            user_id=self.brand_id,
        )

    # ── Read ──────────────────────────────────────────────────────────────────

    def recall(self, query: str, limit: int = 10) -> list[dict]:
        """Semantic search over stored brand memories."""
        results = self._mem.search(query, user_id=self.brand_id, limit=limit)
        # mem0 returns {"results": [...]} or a list depending on version
        if isinstance(results, dict):
            return results.get("results", [])
        return results or []

    def as_context_string(self, query: str) -> str:
        """Return recalled memories as a formatted string for LLM context."""
        memories = self.recall(query)
        if not memories:
            return ""
        lines = []
        for m in memories:
            content = m.get("memory") or m.get("text") or str(m)
            score = m.get("score", 0)
            lines.append(f"[{score:.2f}] {content}" if score else content)
        return "\n".join(lines)
