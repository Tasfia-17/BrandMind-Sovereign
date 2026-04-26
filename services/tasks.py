"""
AgentHansa task handler.

AgentHansa has no public API — so we expose a webhook endpoint that:
1. Accepts inbound tasks (POST /tasks/accept)
2. Routes to the correct service tier
3. Delivers results back via callback URL or stores for pickup (GET /tasks/{id})

This is the real integration pattern for any agent marketplace.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

from fastapi import BackgroundTasks, HTTPException
from pydantic import BaseModel

# In-memory task store (replace with Redis/DB for production)
_tasks: dict[str, dict] = {}


# ── Task models ───────────────────────────────────────────────────────────────

class TaskRequest(BaseModel):
    service: str          # "sovereign_audit" | "campaign_genesis" | "audio_sovereign" | "remediation"
    payload: dict         # service-specific inputs
    callback_url: str | None = None
    buyer_id: str | None = None


class TaskStatus(BaseModel):
    task_id: str
    service: str
    status: str           # "queued" | "running" | "done" | "failed"
    created_at: str
    result: dict | None = None
    error: str | None = None


# ── Task router ───────────────────────────────────────────────────────────────

def _run_task(task_id: str, service: str, payload: dict) -> None:
    """Execute a service tier task. Runs in background."""
    _tasks[task_id]["status"] = "running"
    try:
        from services.tiers import (
            sovereign_audit, campaign_genesis,
            audio_sovereign, autonomous_remediation,
        )

        if service == "sovereign_audit":
            result = sovereign_audit(
                url=payload["url"],
                competitor_urls=payload.get("competitor_urls", []),
            )
        elif service == "campaign_genesis":
            result = campaign_genesis(
                url=payload["url"],
                brief=payload["brief"],
            )
        elif service == "audio_sovereign":
            result = audio_sovereign(
                url=payload["url"],
                campaign_topic=payload["campaign_topic"],
            )
        elif service == "remediation":
            result = autonomous_remediation(
                brand_id=payload["brand_id"],
                violation_report=payload["violation_report"],
                budget=payload.get("budget", 25.0),
            )
        else:
            raise ValueError(f"Unknown service: {service}")

        _tasks[task_id]["status"] = "done"
        _tasks[task_id]["result"] = result

        # Fire callback if provided
        callback = _tasks[task_id].get("callback_url")
        if callback:
            import httpx
            try:
                httpx.post(callback, json={"task_id": task_id, "result": result}, timeout=10)
            except Exception:
                pass

    except Exception as e:
        _tasks[task_id]["status"] = "failed"
        _tasks[task_id]["error"] = str(e)


# ── FastAPI route handlers (imported by api/server.py) ───────────────────────

def accept_task(req: TaskRequest, background_tasks: BackgroundTasks) -> dict:
    """Accept a task and queue it for execution."""
    SERVICE_PRICES = {
        "sovereign_audit": 75,
        "campaign_genesis": 300,
        "audio_sovereign": 200,
        "remediation": 25,
    }
    if req.service not in SERVICE_PRICES:
        raise HTTPException(400, f"Unknown service. Choose: {list(SERVICE_PRICES)}")

    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = {
        "task_id": task_id,
        "service": req.service,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "price": SERVICE_PRICES[req.service],
        "callback_url": req.callback_url,
        "result": None,
        "error": None,
    }

    background_tasks.add_task(_run_task, task_id, req.service, req.payload)

    return {
        "task_id": task_id,
        "status": "queued",
        "service": req.service,
        "price_usd": SERVICE_PRICES[req.service],
        "message": f"Task accepted. Poll GET /tasks/{task_id} for results.",
    }


def get_task(task_id: str) -> dict:
    """Get task status and result."""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")
    return task


def list_tasks() -> dict:
    """List all tasks (for demo/debugging)."""
    return {
        "tasks": list(_tasks.values()),
        "services": {
            "sovereign_audit": {"price": 75, "description": "Multimodal brand compliance scorecard"},
            "campaign_genesis": {"price": 300, "description": "Full kit: copy + image + audio ZIP"},
            "audio_sovereign": {"price": 200, "description": "Audio persona + 3 scripts + synthesized spots"},
            "remediation": {"price": "25-50", "description": "Detect violation → hire specialist → verify → pay"},
        },
    }
