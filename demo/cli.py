"""
BrandMind Sovereign — CLI demo.

Runs the exact 1-minute demo flow:
  1. Ingest a brand website → build memory
  2. Generate copy (session 1)
  3. Cold-start new session → recall memory → generate again (proves persistence)
  4. Show auto-generated SKILL.md
  5. Synthesize audio via Fish Audio
"""
from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from pathlib import Path
import subprocess
import sys

from agent.ingestion import ingest_brand
from agent.core import BrandMindAgent
from memory.brand_memory import BrandMemory
from audio.tts import synthesize, brand_speed

app = typer.Typer(help="BrandMind Sovereign — Autonomous Brand Voice Agent")
console = Console()


@app.command()
def demo(
    url: str = typer.Argument(..., help="Brand website URL to ingest"),
    task: str = typer.Option(
        "Write a launch tweet about our product",
        "--task", "-t",
        help="Content generation task",
    ),
):
    """Run the full BrandMind demo: ingest → generate → recall → skill → audio."""

    console.print(Panel.fit(
        "[bold cyan]BrandMind Sovereign[/bold cyan]\n"
        "[dim]Autonomous Brand Voice Agent — AI Agent Economy Hackathon 2026[/dim]",
        border_style="cyan",
    ))

    # ── Step 1: Ingest ────────────────────────────────────────────────────────
    console.print("\n[bold yellow]Step 1:[/bold yellow] Ingesting brand from website...")
    profile, memory = ingest_brand(url)
    brand_id = memory.brand_id

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("[dim]Brand[/dim]", f"[bold]{profile.brand_name}[/bold]")
    table.add_row("[dim]Tone[/dim]", profile.tone_summary[:80])
    table.add_row("[dim]Formality[/dim]", f"{profile.formality}/10")
    table.add_row("[dim]Taboo words[/dim]", ", ".join(profile.taboo_words[:3]))
    table.add_row("[dim]Stored in[/dim]", f"[green]HydraDB → brandmind/{brand_id}[/green]")
    console.print(table)

    # ── Step 2: Generate (Session 1) ─────────────────────────────────────────
    console.print(f"\n[bold yellow]Step 2:[/bold yellow] Generating copy (Session 1)...")
    console.print(f"  Task: [italic]{task}[/italic]")

    agent = BrandMindAgent(brand_id, memory, profile.tone_summary)
    result1 = agent.run(task)

    console.print(Panel(
        result1["result"],
        title=f"[green]Generated Copy[/green] ({result1['tool_calls']} tool calls, {result1['duration_ms']}ms)",
        border_style="green",
    ))

    # ── Step 3: Cold-start recall (Session 2) ─────────────────────────────────
    console.print("\n[bold yellow]Step 3:[/bold yellow] [bold red]NEW SESSION[/bold red] — cold start, no re-briefing...")
    console.print("  [dim]Creating fresh agent with no prior context...[/dim]")

    fresh_memory = BrandMemory(brand_id)  # new instance, loads from HydraDB
    fresh_agent = BrandMindAgent(brand_id, fresh_memory)
    result2 = fresh_agent.run(f"Write a LinkedIn bio for {profile.brand_name}")

    console.print(Panel(
        result2["result"],
        title="[green]Recalled from HydraDB — zero re-briefing[/green]",
        border_style="green",
    ))

    recalled = fresh_memory.as_context_string("brand voice tone")
    if recalled:
        console.print(f"\n[dim]HydraDB recall (alpha=0.8):[/dim]")
        for line in recalled.split("\n")[:3]:
            console.print(f"  [dim]{line}[/dim]")

    # ── Step 4: Skill auto-generation ─────────────────────────────────────────
    skill_path = result1.get("skill_generated") or result2.get("skill_generated")
    if not skill_path:
        # Force it by running one more task to hit the threshold
        for _ in range(3):
            r = agent.run("Write a 15-second audio ad script")
            if r.get("skill_generated"):
                skill_path = r["skill_generated"]
                break

    if skill_path and Path(skill_path).exists():
        console.print(f"\n[bold yellow]Step 4:[/bold yellow] Auto-generated SKILL.md")
        skill_content = Path(skill_path).read_text()
        console.print(Syntax(skill_content[:600], "markdown", theme="monokai"))
        console.print(f"  [green]✓ Saved to: {skill_path}[/green]")
        console.print("  [dim]Drop this into any Hermes instance → instant brand voice, zero config.[/dim]")

    # ── Step 5: Fish Audio TTS ─────────────────────────────────────────────────
    console.print(f"\n[bold yellow]Step 5:[/bold yellow] Synthesizing audio via Fish Audio...")
    audio_text = result1["result"][:200]  # first 200 chars
    audio_path = synthesize(
        audio_text,
        filename=f"{brand_id}_demo.mp3",
        speed=brand_speed(profile.audio_pace),
    )
    console.print(f"  [green]✓ Audio saved: {audio_path}[/green]")
    console.print(f"  [dim]Pace: {profile.audio_pace} → speed={brand_speed(profile.audio_pace)}x[/dim]")

    # Try to play audio if mpg123 or afplay available
    for player in ["mpg123", "afplay", "ffplay"]:
        try:
            subprocess.run([player, str(audio_path)], capture_output=True, timeout=10)
            break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    # ── Summary ───────────────────────────────────────────────────────────────
    console.print(Panel.fit(
        f"[bold green]✓ Demo complete[/bold green]\n\n"
        f"Brand: [bold]{profile.brand_name}[/bold] ({brand_id})\n"
        f"Memory: [green]Stored in HydraDB[/green] — persists across all future sessions\n"
        f"Skill: [green]{Path(skill_path).name if skill_path else 'pending (need 5+ tool calls)'}[/green]\n"
        f"Audio: [green]{audio_path.name}[/green]\n"
        f"BotLearn: [green]Karma logged[/green]\n\n"
        f"[dim]This agent runs 24/7. Every session makes it smarter.[/dim]",
        border_style="green",
        title="BrandMind Sovereign",
    ))


@app.command()
def ingest(url: str, brand_id: str = typer.Option(None)):
    """Ingest a brand website into HydraDB memory."""
    profile, memory = ingest_brand(url, brand_id)
    console.print(f"[green]✓[/green] Ingested [bold]{profile.brand_name}[/bold] → {memory.brand_id}")


@app.command()
def generate(brand_id: str, task: str):
    """Generate brand-compliant copy for a brand."""
    memory = BrandMemory(brand_id)
    agent = BrandMindAgent(brand_id, memory)
    result = agent.run(task)
    console.print(Panel(result["result"], title=f"[green]{brand_id}[/green]"))


@app.command()
def speak(brand_id: str, text: str, output: str = "output.mp3"):
    """Synthesize text to audio using the brand's voice persona."""
    memory = BrandMemory(brand_id)
    pace_ctx = memory.recall("audio pace")
    pace = "moderate"
    for m in pace_ctx:
        c = str(m.get("chunk_content", ""))
        if "slow" in c:
            pace = "slow"
        elif "fast" in c:
            pace = "fast"
    path = synthesize(text, output, speed=brand_speed(pace))
    console.print(f"[green]✓[/green] Audio saved: {path}")


if __name__ == "__main__":
    app()
