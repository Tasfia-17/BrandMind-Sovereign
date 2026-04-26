"""
TokenRouter multi-model routing.

Each task type routes to the optimal model:
  extraction  → deepseek-chat        (cheap, fast, structured)
  generation  → claude-sonnet-4      (best copy quality)
  vision      → gpt-4o               (image/screenshot analysis)
  image       → fal-ai/flux-schnell  (via fal.ai, not TokenRouter)
  audio_script→ claude-sonnet-4      (nuanced tone)
"""
from __future__ import annotations

from enum import Enum
from openai import OpenAI
from agent.config import TOKENROUTER_API_KEY, TOKENROUTER_BASE_URL

# Model aliases on TokenRouter
MODELS = {
    "extraction": "deepseek/deepseek-v3.2",
    "generation": "anthropic/claude-sonnet-4",
    "vision":     "openai/gpt-4o-mini",
    "embedding": "openai/gpt-4o-mini",
    "audio":      "anthropic/claude-sonnet-4",
    "fast":       "deepseek/deepseek-v4-flash",
}


class RouteType(str, Enum):
    EXTRACTION   = "extraction"
    GENERATION   = "generation"
    VISION       = "vision"
    AUDIO        = "audio"
    FAST         = "fast"


def get_client() -> OpenAI:
    return OpenAI(api_key=TOKENROUTER_API_KEY, base_url=TOKENROUTER_BASE_URL)


def route(
    route_type: RouteType,
    messages: list[dict],
    *,
    json_mode: bool = False,
    temperature: float = 0.7,
    tools: list | None = None,
    tool_choice: str = "auto",
) -> str:
    """Route a completion request to the right model. Returns content string."""
    client = get_client()
    model = MODELS[route_type.value]

    kwargs: dict = dict(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice

    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def route_with_tools(
    route_type: RouteType,
    messages: list[dict],
    tools: list[dict],
) -> object:
    """Route and return the full message object (for tool-call loops)."""
    client = get_client()
    model = MODELS[route_type.value]
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.7,
    )
    return resp.choices[0].message
