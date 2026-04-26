# BrandMind Sovereign
**Autonomous Brand Voice Agent — AI Agent Economy Hackathon 2026**

An agent that remembers your brand voice across sessions, generates compliant content, and gets smarter with every task.

## Architecture

```
Website URL
    ↓
[Ingestion] scrape + LLM extract → BrandProfile
    ↓
[HydraDB] store brand memory (persists across sessions)
    ↓
[Agent Loop] recall → generate → audit (TokenRouter LLM)
    ↓
[Skill Auto-gen] writes brand-voice.skill.md after 5+ tool calls
    ↓
[Fish Audio] synthesizes output in brand's voice persona
    ↓
[BotLearn] logs karma for every execution
```

## API Keys Needed

| Key | Where to Get | Env Var |
|-----|-------------|---------|
| TokenRouter | https://bit.ly/4eG9ddG (hackathon voucher) | `TOKENROUTER_API_KEY` |
| HydraDB | https://hydradb.com OR ask Nishkarsh at the event | `HYDRADB_API_KEY` |
| Fish Audio | https://fish.audio/auth/ → API Keys | `FISH_API_KEY` |
| BotLearn | https://www.botlearn.ai → settings | `BOTLEARN_API_KEY` |

## Setup

```bash
cd brandmind
cp .env.example .env
# Fill in your API keys in .env

pip install -e .
```

## Run the Demo

```bash
# Full 1-minute demo flow (ingest → generate → recall → skill → audio)
python main.py demo https://stripe.com

# Or try any brand:
python main.py demo https://vercel.com --task "Write a launch tweet about our new edge runtime"
python main.py demo https://linear.app --task "Write a LinkedIn bio"
```

## API Server

```bash
uvicorn api.server:app --reload --port 8000
# Docs: http://localhost:8000/docs
```

## What the Demo Shows

1. **Ingest** — scrapes real website, extracts brand voice profile via LLM
2. **Generate** — agent recalls memory, generates on-brand copy
3. **Cold-start recall** — NEW session, zero re-briefing, HydraDB returns full context
4. **Skill auto-gen** — after 5+ tool calls, agent writes `brand-id.skill.md`
5. **Audio** — Fish Audio synthesizes copy in brand's voice persona

## The Winning Moment (for judges)

The cold-start recall at step 3. A fresh agent instance with no prior context
generates perfectly on-brand copy because HydraDB remembered everything.

Say to judges: *"HydraDB's hybrid recall (alpha=0.8) pulled tone, audience, and
brand relationships as a ranked context bundle — that's relational memory, not
a vector lookup."*
