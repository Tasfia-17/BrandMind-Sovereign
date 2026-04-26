"""
BrandMind Agent Core.

Implements a tool-using agent loop that:
1. Recalls brand memory from HydraDB before every generation
2. Generates brand-compliant content via TokenRouter
3. Auto-generates a SKILL.md after 5+ tool calls (Hermes pattern)
4. Logs every execution to BotLearn
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from agent.router import route, route_with_tools, RouteType, get_client
from memory.brand_memory import BrandMemory
from training.botlearn import BotLearnLogger

SKILLS_DIR = Path(__file__).parent.parent / "skills"
SKILLS_DIR.mkdir(exist_ok=True)


# ── Tool definitions (OpenAI function-calling format) ─────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "recall_brand_memory",
            "description": "Retrieve stored brand voice facts from HydraDB memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to recall about the brand"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_copy",
            "description": "Generate brand-compliant marketing copy (tagline, bio, tweet, email, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "content_type": {
                        "type": "string",
                        "enum": ["tagline", "bio", "tweet", "email", "landing_page", "ad_script"],
                    },
                    "topic": {"type": "string", "description": "What the copy is about"},
                    "brand_context": {"type": "string", "description": "Brand voice facts to apply"},
                },
                "required": ["content_type", "topic", "brand_context"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "audit_brand_compliance",
            "description": "Check if a piece of copy complies with the brand voice.",
            "parameters": {
                "type": "object",
                "properties": {
                    "copy": {"type": "string"},
                    "brand_context": {"type": "string"},
                },
                "required": ["copy", "brand_context"],
            },
        },
    },
]


# ── Tool implementations ───────────────────────────────────────────────────────

def _tool_recall(memory: BrandMemory, query: str) -> str:
    context = memory.as_context_string(query)
    return context if context else "No brand memory found yet. Proceeding with defaults."


def _tool_generate_copy(content_type: str, topic: str, brand_context: str) -> str:
    prompt = f"""You are a brand copywriter. Generate {content_type} copy about: {topic}

Brand voice rules (follow strictly):
{brand_context}

Output ONLY the copy itself, no explanation."""
    return route(RouteType.GENERATION, [{"role": "user", "content": prompt}], temperature=0.7)


def _tool_audit(copy: str, brand_context: str) -> str:
    prompt = f"""Audit this copy for brand voice compliance.

Brand rules:
{brand_context}

Copy to audit:
{copy}

Return JSON: {{"compliant": bool, "score": 0-100, "issues": [str], "fixes": [str]}}"""
    return route(RouteType.FAST, [{"role": "user", "content": prompt}], json_mode=True, temperature=0.1)


def _dispatch_tool(name: str, args: dict, memory: BrandMemory) -> str:
    if name == "recall_brand_memory":
        return _tool_recall(memory, args["query"])
    elif name == "generate_copy":
        return _tool_generate_copy(args["content_type"], args["topic"], args["brand_context"])
    elif name == "audit_brand_compliance":
        return _tool_audit(args["copy"], args["brand_context"])
    return f"Unknown tool: {name}"


# ── Skill auto-generation (Hermes pattern) ────────────────────────────────────

def _maybe_write_skill(brand_id: str, tool_call_count: int, profile_summary: str) -> str | None:
    """After 5+ tool calls, auto-generate a SKILL.md for this brand."""
    if tool_call_count < 5:
        return None
    skill_path = SKILLS_DIR / f"{brand_id}.skill.md"
    if skill_path.exists():
        return None  # already written

    content = f"""---
name: {brand_id}-brand-voice
description: Auto-generated brand voice skill for {brand_id}
version: 1.0.0
generated_by: BrandMind Sovereign
tool_calls_to_generate: {tool_call_count}
metadata:
  tags: [brand-voice, marketing, auto-generated]
  category: brand
---

# {brand_id} Brand Voice Skill

## When to Use
Use this skill when generating any content for {brand_id}.
Drop this file into any Hermes instance to instantly apply this brand's voice.

## Brand Profile
{profile_summary}

## Procedure
1. Call `recall_brand_memory` with query matching the content type needed
2. Apply recalled voice rules strictly — especially taboo words and sentence style
3. Call `generate_copy` with the recalled context
4. Call `audit_brand_compliance` to verify output
5. If score < 80, regenerate with stricter constraints

## Notes
- This skill was auto-generated after {tool_call_count} successful tool calls
- Memory is stored in HydraDB under tenant: brandmind / {brand_id}
"""
    skill_path.write_text(content)
    return str(skill_path)


# ── Main agent loop ────────────────────────────────────────────────────────────

class BrandMindAgent:
    def __init__(self, brand_id: str, memory: BrandMemory, profile_summary: str = "") -> None:
        self.brand_id = brand_id
        self.memory = memory
        self.profile_summary = profile_summary
        self._tool_call_count = 0
        self._botlearn = BotLearnLogger()

    def run(self, task: str) -> dict[str, Any]:
        """
        Run the agent on a task. Returns:
        {result, tool_calls, skill_generated, duration_ms}
        """
        start = time.time()
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are BrandMind Sovereign, an autonomous brand voice agent for '{self.brand_id}'.\n"
                    "Always recall brand memory before generating any content.\n"
                    "Use tools in this order: recall → generate → audit.\n"
                    "Never invent brand rules — only use what memory returns."
                ),
            },
            {"role": "user", "content": task},
        ]

        result = ""
        skill_path = None

        # Agentic loop — runs until no more tool calls
        while True:
            msg = route_with_tools(RouteType.GENERATION, messages, TOOLS)

            if not msg.tool_calls:
                result = msg.content or ""
                break

            # Execute all tool calls in this turn
            messages.append(msg)
            for tc in msg.tool_calls:
                self._tool_call_count += 1
                args = json.loads(tc.function.arguments)
                tool_result = _dispatch_tool(tc.function.name, args, self.memory)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result,
                })

            # Check if we should auto-generate a skill
            if not skill_path:
                skill_path = _maybe_write_skill(
                    self.brand_id, self._tool_call_count, self.profile_summary
                )

        duration_ms = int((time.time() - start) * 1000)

        # Log to BotLearn
        self._botlearn.log_execution(
            agent_name="brandmind-sovereign",
            skill_id=self.brand_id,
            status="success",
            duration_ms=duration_ms,
            tokens=self._tool_call_count * 200,  # estimate
        )

        return {
            "result": result,
            "tool_calls": self._tool_call_count,
            "skill_generated": skill_path,
            "duration_ms": duration_ms,
        }
