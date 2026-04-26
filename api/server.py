"""
BrandMind Sovereign — FastAPI server v3.0

Routes:
  POST /ingest                  Scrape website → build brand memory
  POST /generate                Generate brand-compliant copy (agent loop)
  POST /audit                   Check copy compliance
  POST /speak                   Synthesize copy to audio
  GET  /memory/{brand}          Show stored brand memory

  POST /tasks/accept            Accept AgentHansa task (queued, async)
  GET  /tasks/{id}              Poll task status + result
  GET  /tasks                   List all tasks + service catalog

  POST /services/audit          Sovereign Audit $75 (sync)
  POST /services/campaign       Campaign Genesis $300 (sync)
  POST /services/audio          Audio Sovereign $200 (sync)
  POST /services/remediation    Autonomous Remediation $25-50 (sync)
"""
from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agent.ingestion import ingest_brand
from agent.core import BrandMindAgent
from memory.brand_memory import BrandMemory
from audio.tts import synthesize, brand_speed
from services.tasks import TaskRequest, accept_task, get_task, list_tasks

app = FastAPI(title="BrandMind Sovereign", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Core models ───────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    url: str
    brand_id: str | None = None

class GenerateRequest(BaseModel):
    brand_id: str
    task: str

class AuditRequest(BaseModel):
    brand_id: str
    content: str

class SpeakRequest(BaseModel):
    brand_id: str
    text: str
    filename: str = "output.mp3"

class AuditServiceRequest(BaseModel):
    url: str
    competitor_urls: list[str] = []

class CampaignRequest(BaseModel):
    url: str
    brief: str

class AudioServiceRequest(BaseModel):
    url: str
    campaign_topic: str

class RemediationRequest(BaseModel):
    brand_id: str
    violation_report: str
    budget: float = 25.0


# ── Core endpoints ────────────────────────────────────────────────────────────

@app.post("/ingest")
def ingest(req: IngestRequest):
    try:
        profile, memory = ingest_brand(req.url, req.brand_id)
        return {"brand_id": memory.brand_id, "profile": profile.model_dump()}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/generate")
def generate(req: GenerateRequest):
    memory = BrandMemory(req.brand_id)
    agent = BrandMindAgent(req.brand_id, memory, memory.as_context_string("brand voice"))
    return agent.run(req.task)


@app.post("/audit")
def audit(req: AuditRequest):
    memory = BrandMemory(req.brand_id)
    agent = BrandMindAgent(req.brand_id, memory)
    return agent.run(f"Audit this copy:\n\n{req.content}")


@app.post("/speak")
def speak(req: SpeakRequest):
    memory = BrandMemory(req.brand_id)
    pace_mems = memory.recall("audio pace")
    pace = next(
        (("slow" if "slow" in str(m) else "fast") for m in pace_mems if "slow" in str(m) or "fast" in str(m)),
        "moderate",
    )
    path = synthesize(req.text, req.filename, speed=brand_speed(pace))
    return FileResponse(str(path), media_type="audio/mpeg", filename=req.filename)


@app.get("/memory/{brand_id}")
def get_memory(brand_id: str, query: str = "brand voice tone style"):
    return {"brand_id": brand_id, "memories": BrandMemory(brand_id).recall(query)}


# ── AgentHansa task queue ─────────────────────────────────────────────────────

@app.post("/tasks/accept")
def task_accept(req: TaskRequest, background_tasks: BackgroundTasks):
    return accept_task(req, background_tasks)


@app.get("/tasks/{task_id}")
def task_status(task_id: str):
    return get_task(task_id)


@app.get("/tasks")
def task_list():
    return list_tasks()


# ── Service tier endpoints (synchronous) ─────────────────────────────────────

@app.post("/services/audit")
def service_audit(req: AuditServiceRequest):
    """Sovereign Audit — $75"""
    from services.tiers import sovereign_audit
    try:
        return sovereign_audit(req.url, req.competitor_urls)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/services/campaign")
def service_campaign(req: CampaignRequest):
    """Campaign Genesis — $300"""
    from services.tiers import campaign_genesis
    try:
        return campaign_genesis(req.url, req.brief)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/services/audio")
def service_audio(req: AudioServiceRequest):
    """Audio Sovereign — $200"""
    from services.tiers import audio_sovereign
    try:
        return audio_sovereign(req.url, req.campaign_topic)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/services/remediation")
def service_remediation(req: RemediationRequest):
    """Autonomous Remediation — $25-50"""
    from services.tiers import autonomous_remediation
    try:
        return autonomous_remediation(req.brand_id, req.violation_report, req.budget)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/")
def root():
    return {
        "name": "BrandMind Sovereign",
        "version": "3.0.0",
        "services": {
            "sovereign_audit": "$75 — POST /services/audit",
            "campaign_genesis": "$300 — POST /services/campaign",
            "audio_sovereign": "$200 — POST /services/audio",
            "remediation": "$25-50 — POST /services/remediation",
        },
        "tasks": "POST /tasks/accept → GET /tasks/{id}",
    }

@app.get("/health")
def health():
    return {"status": "ok", "version": "3.0.0"}

@app.on_event("startup")
async def startup():
    print("BrandMind Sovereign v3.0 started")
    print("AgentHansa profile: https://www.agenthansa.com/experts/brandmind-sovereign")
