# Contributing

## Adding a new service tier

1. Add implementation in `services/tiers.py`
2. Add endpoint in `api/server.py`
3. Add task routing in `services/tasks.py`
4. Add AgentHansa service declaration in `agenthansa/register.py`

## Adding a new model route

Edit `agent/router.py` MODELS dict. All models must be available on TokenRouter.

## Memory

All brand memory goes through `memory/brand_memory.py`. Never call Mem0 directly from service code.
