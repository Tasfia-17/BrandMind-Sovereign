"""
BotLearn karma logger.

Logs every agent skill execution to BotLearn for reputation/karma tracking.
"""
from __future__ import annotations

import httpx

from agent.config import BOTLEARN_API_KEY

_BASE = "https://www.botlearn.ai/api/v2"
_HEADERS = {"Authorization": f"Bearer {BOTLEARN_API_KEY}"}


class BotLearnLogger:
    def __init__(self) -> None:
        self._registered = False

    def _register(self) -> None:
        if self._registered:
            return
        try:
            httpx.post(
                f"{_BASE}/agents/register",
                headers=_HEADERS,
                json={"agentName": "brandmind-sovereign", "platform": "custom"},
                timeout=5,
            )
            self._registered = True
        except Exception:
            pass  # non-fatal — BotLearn is a bonus, not core

    def log_execution(
        self,
        agent_name: str,
        skill_id: str,
        status: str,
        duration_ms: int,
        tokens: int,
    ) -> None:
        self._register()
        try:
            httpx.post(
                f"{_BASE}/solutions/run-report",
                headers=_HEADERS,
                json={
                    "agentName": agent_name,
                    "skillId": skill_id,
                    "status": status,
                    "duration_ms": duration_ms,
                    "tokens": tokens,
                },
                timeout=5,
            )
        except Exception:
            pass  # non-fatal
