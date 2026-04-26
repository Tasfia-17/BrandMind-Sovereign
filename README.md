# BrandMind Sovereign

Autonomous multimodal brand voice agent. Audits brand compliance, generates campaign kits (copy + image + audio), builds audio personas, and remediates brand violations. Memory persists across sessions using Mem0 vector store.

## What It Does

Most marketing teams spend thousands per month on agencies to keep brand voice consistent across channels. BrandMind Sovereign automates this entirely. Give it a website URL and it builds a persistent brand memory, then generates on-brand content for any task without re-briefing.

### Four Services

| Service | Price | Deliverable |
|---------|-------|-------------|
| Sovereign Audit | $75 | Multimodal brand compliance scorecard with competitor analysis |
| Campaign Genesis | $300 | ZIP kit: copy + hero image (flux-schnell) + synthesized audio spots |
| Audio Sovereign | $200 | Audio persona + 15s/30s/60s scripts + MP3 files via Fish Audio |
| Autonomous Remediation | $25-50 | Violation detection + x402 payment mandate + memory update |

## Architecture

```
Website URL
    |
[Ingestion Pipeline]
    scrape (httpx + BeautifulSoup)
    extract brand profile (deepseek/deepseek-v3.2 via TokenRouter)
    store in Mem0 (vector + graph dual store)
    |
[BrandMind Agent Loop]
    recall brand memory (Mem0 semantic search)
    generate copy (anthropic/claude-sonnet-4 via TokenRouter)
    audit compliance (deepseek/deepseek-v4-flash via TokenRouter)
    |
[Multimodal Output]
    images: fal.ai flux-schnell (~$0.003/image)
    audio: Fish Audio TTS (pace/energy from brand memory)
    kit: ZIP assembly (copy.md + image + audio)
    |
[Skill Auto-generation]
    after 5+ tool calls: writes {brand_id}.skill.md
    encodes brand patterns as reusable OpenClaw skill
    |
[AgentHansa Integration]
    long-poll loop receives tasks from merchants
    routes to correct service tier
    delivers results + replies via engagement API
    |
[x402 Payments]
    sub-agent hiring via x402 open protocol (Base mainnet)
    payment mandate creation + verification
    USDC settlement via Coinbase facilitator
```

## Tech Stack

- **Agent framework**: Tool-using loop with OpenAI function-calling format
- **Memory**: Mem0 (vector store via local Qdrant + knowledge graph)
- **LLM routing**: TokenRouter (deepseek for extraction, claude for generation, gpt-4o-mini for vision)
- **Image generation**: fal.ai flux-schnell
- **Audio synthesis**: Fish Audio TTS SDK
- **Payments**: x402 open protocol (coinbase/x402)
- **Marketplace**: AgentHansa (task acceptance + delivery via long-poll)
- **API**: FastAPI
- **Training logs**: BotLearn karma API

## Setup

```bash
git clone https://github.com/Tasfia-17/BrandMind-Sovereign.git
cd BrandMind-Sovereign
pip install -e .
cp .env.example .env
```

Edit `.env` and fill in:

```
TOKENROUTER_API_KEY=your_key        # https://tokenrouter.com
FISH_API_KEY=your_key               # https://fish.audio/app/api-keys/
FAL_API_KEY=your_key                # https://fal.ai/dashboard
AGENTHANSA_KEY=your_tabb_key        # run: python -m agenthansa.register
EVM_WALLET_ADDRESS=your_address     # your Base mainnet wallet address
```

## Run

```bash
# CLI demo: ingest a brand and generate content
python main.py demo https://stripe.com --task "Write a launch tweet for our new billing API"

# API server
uvicorn api.server:app --port 8000
# Docs: http://localhost:8000/docs

# AgentHansa worker (receives tasks from merchants)
python -m agenthansa.loop

# Register on AgentHansa (run once)
python -m agenthansa.register
```

## API Endpoints

```
GET  /                          Service catalog
POST /ingest                    Scrape website and build brand memory
POST /generate                  Generate brand-compliant copy (agent loop)
POST /audit                     Check copy compliance
POST /speak                     Synthesize text to audio

POST /services/audit            Sovereign Audit ($75)
POST /services/campaign         Campaign Genesis ($300)
POST /services/audio            Audio Sovereign ($200)
POST /services/remediation      Autonomous Remediation ($25-50)

POST /tasks/accept              Accept AgentHansa task (async)
GET  /tasks/{id}                Poll task status and result
GET  /tasks                     List all tasks and service catalog
GET  /memory/{brand_id}         Show stored brand memory
```

## Demo Flow

The CLI demo runs five steps automatically:

1. Scrapes the target website and extracts a structured brand profile (name, tone, formality, taboo words, audio pace/energy, ICP)
2. Stores the profile in Mem0 vector store under the brand's tenant ID
3. Runs the agent loop: recall memory, generate copy, audit compliance
4. Starts a fresh agent instance with no prior context and recalls the same brand memory from Mem0 (proves cross-session persistence)
5. Auto-generates a `{brand_id}.skill.md` file after 5+ tool calls, then synthesizes the output as audio via Fish Audio

## Memory System

Brand memory is stored in Mem0 with two layers:

- **Vector store** (local Qdrant): semantic similarity search over brand facts
- **Knowledge graph**: relationship traversal between brand entities

Each brand is isolated by `user_id` (the brand's domain slug). Memory persists across all sessions and agent restarts. A fresh agent instance with no prior context can recall the full brand profile from a previous session.

## Skill Auto-generation

After 5 or more tool calls on a brand, the agent writes a `SKILL.md` file encoding the brand's voice patterns. This file can be dropped into any OpenClaw or Hermes agent instance to instantly apply the brand voice without re-ingestion.

## Payment Flow (x402)

For Autonomous Remediation tasks, the agent creates an x402 payment mandate:

1. Classifies the violation type and estimates cost ($25-50)
2. Creates a payment mandate with `pay_to` set to the configured EVM wallet
3. Embeds the mandate in the AgentHansa task post for specialist agents
4. Verifies payment via the Coinbase public facilitator at `x402.org/facilitator`
5. Updates brand memory with the new constraint after verification

## Project Structure

```
brandmind/
    agent/
        config.py       environment and model config
        core.py         tool-using agent loop + skill auto-generation
        ingestion.py    website scraping + brand profile extraction
        router.py       TokenRouter multi-model routing
    memory/
        brand_memory.py Mem0 vector + graph memory layer
    services/
        tiers.py        four service tier implementations
        kit.py          campaign ZIP assembly
        payments.py     x402 payment mandate creation and verification
        tasks.py        AgentHansa task queue and routing
    agenthansa/
        register.py     one-time registration script
        loop.py         long-poll expert worker
    api/
        server.py       FastAPI application
    audio/
        tts.py          Fish Audio TTS synthesis
    images/
        gen.py          fal.ai flux-schnell image generation
    training/
        botlearn.py     BotLearn karma logger
    demo/
        cli.py          rich CLI demo runner
    main.py             entry point
```
