#!/usr/bin/env python3
"""
Signal Archive populate CLI.

Seed the archive with realistic research or record reuse of existing work.

Usage:
    python scripts/populate_archive.py [OPTIONS]

  --topic TEXT           Research topic / question
  --depth [low|mid|high] Research depth
  --new-user             Create a fresh realistic contributor persona
  --api-key TEXT         Contributor API key (overrides SIGNAL_ARCHIVE_API_KEY env var)
"""
import asyncio
import json
import os
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
import httpx

try:
    from anthropic import Anthropic
except ImportError:
    click.echo("anthropic package required: pip install anthropic", err=True)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))
from worker_sdk import ArchiveClient, ArtifactPayload, Citation

ARCHIVE_BASE = os.environ.get("SIGNAL_ARCHIVE_API_URL", "https://signal-archive-api.fly.dev")
REUSE_THRESHOLD = 0.80

DEPTH_CONFIG = {
    "low":  {"min_refs": 5,  "max_refs": 10, "min_words": 500,  "max_words": 800,  "label": "brief"},
    "mid":  {"min_refs": 10, "max_refs": 20, "min_words": 1500, "max_words": 2000, "label": "thorough"},
    "high": {"min_refs": 20, "max_refs": 35, "min_words": 3000, "max_words": 5000, "label": "comprehensive deep dive"},
}

# ─────────────────────────────────────────────────────────────────────────────
# Persona generation
# ─────────────────────────────────────────────────────────────────────────────

def _generate_persona(client: Anthropic) -> dict:
    """Ask Claude to invent a realistic AI/ML researcher persona."""
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": (
                "Generate a realistic researcher persona for an AI/ML knowledge base. "
                "The person should be a credible tech professional — could be an academic, "
                "industry researcher, or senior engineer. Make them feel real and varied: "
                "mix of genders, nationalities, specialties. "
                "Return ONLY a JSON object, no markdown:\n"
                '{"display_name": "Full Name", "handle_base": "lowercase-slug-10-18-chars", '
                '"specialty": "one-sentence research focus"}'
            ),
        }],
    )
    raw = msg.content[0].text.strip()
    # Strip markdown code fences if present
    raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
    data = json.loads(raw)
    # Ensure handle is valid and unique
    base = re.sub(r"[^a-z0-9-]", "-", data["handle_base"].lower()).strip("-")[:18]
    data["handle"] = f"{base}-{secrets.token_hex(3)}"
    return data


def _register_contributor(handle: str, display_name: str) -> str:
    """Register a new contributor and return their API key."""
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{ARCHIVE_BASE}/contributors",
            json={"handle": handle, "display_name": display_name},
        )
        if resp.status_code == 409:
            raise click.ClickException(f"Handle '{handle}' is already taken.")
        resp.raise_for_status()
    return resp.json()["api_key"]


# ─────────────────────────────────────────────────────────────────────────────
# Archive search + reuse
# ─────────────────────────────────────────────────────────────────────────────

def _search(topic: str, limit: int = 5) -> list:
    """Search archive and return matches above the reuse threshold."""
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{ARCHIVE_BASE}/search", params={"q": topic, "limit": limit})
        resp.raise_for_status()
    return [m for m in resp.json() if m["similarity"] >= REUSE_THRESHOLD]


def _record_reuse(canonical_id: str, n: int = 3) -> None:
    """Record n reuse events for a canonical question."""
    with httpx.Client(timeout=15) as client:
        for _ in range(n):
            client.post(
                f"{ARCHIVE_BASE}/canonical/{canonical_id}/reuse",
                params={"reused_by": "populate_cli"},
            )


# ─────────────────────────────────────────────────────────────────────────────
# Research generation
# ─────────────────────────────────────────────────────────────────────────────

_RESEARCH_SYSTEM = """\
You are a rigorous researcher writing a report for Signal Archive, \
a public AI/ML knowledge base. Your reports are well-structured, cite \
real sources (papers on arXiv, IEEE, conference proceedings, official docs, \
research blog posts from Google DeepMind, OpenAI, NVIDIA, etc.), \
and are written in authoritative but accessible prose.

IMPORTANT: All citation URLs must be plausible real URLs. \
Use actual arXiv paper IDs where applicable. Do not invent domains."""

def _build_research_prompt(topic: str, depth: str) -> str:
    cfg = DEPTH_CONFIG[depth]
    return (
        f"Research topic: {topic}\n\n"
        f"Write a {cfg['label']} research report ({cfg['min_words']}–{cfg['max_words']} words in the body, "
        f"{cfg['min_refs']}–{cfg['max_refs']} citations).\n\n"
        "Return ONLY a JSON object — no markdown fences, no commentary:\n"
        "{\n"
        '  "cleaned_question": "canonical phrasing of the research question",\n'
        '  "short_answer": "2-3 sentence TL;DR answer to the question",\n'
        '  "full_body": "full markdown research body",\n'
        '  "citations": [\n'
        '    {"url": "https://...", "title": "Paper or page title", "domain": "domain.com"}\n'
        "  ]\n"
        "}"
    )


def _generate_research(client: Anthropic, topic: str, depth: str) -> dict:
    cfg = DEPTH_CONFIG[depth]
    # Use a more capable model for mid/high depth
    model = "claude-opus-4-7" if depth == "high" else "claude-sonnet-4-6"
    max_tokens = {
        "low":  2048,
        "mid":  6000,
        "high": 12000,
    }[depth]

    click.echo(f"  Generating {cfg['label']} research with {model}…")
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=_RESEARCH_SYSTEM,
        messages=[{"role": "user", "content": _build_research_prompt(topic, depth)}],
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
    data = json.loads(raw)

    # Validate minimum citation count
    n_refs = len(data.get("citations", []))
    if n_refs < cfg["min_refs"]:
        click.echo(
            f"  ⚠  Got {n_refs} citations (expected ≥{cfg['min_refs']}). "
            "Submitting anyway.",
            err=True,
        )
    return data


# ─────────────────────────────────────────────────────────────────────────────
# Submission
# ─────────────────────────────────────────────────────────────────────────────

async def _submit(api_key: str, research: dict, topic: str) -> str:
    payload = ArtifactPayload(
        cleaned_question=research["cleaned_question"],
        cleaned_prompt=topic,
        short_answer=research["short_answer"],
        full_body=research["full_body"],
        citations=[Citation(**c) for c in research["citations"]],
        run_date=datetime.now(timezone.utc),
        worker_type="claude-code",
        model_info="claude-sonnet-4-6",
        source_domains=list({c["domain"] for c in research["citations"]}),
        prompt_modified=False,
    )
    client = ArchiveClient()
    # Override API key from env for this call
    client.api_key = api_key
    return await client.submit(payload)


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

@click.command()
@click.option("--topic",    default=None, help="Research topic or question.")
@click.option("--depth",    default=None, type=click.Choice(["low", "mid", "high"]),
              help="low=5-10 refs, mid=10-20 refs, high=20+ refs.")
@click.option("--new-user", is_flag=True,  help="Create a fresh realistic contributor persona.")
@click.option("--api-key",  default=None,  help="Contributor API key (overrides SIGNAL_ARCHIVE_API_KEY env var).")
def main(topic, depth, new_user, api_key):
    """Populate Signal Archive with research or record reuse of existing work.

    Requires ANTHROPIC_API_KEY to be set in the environment.
    Optionally set SIGNAL_ARCHIVE_API_KEY to submit as an existing contributor.

    Examples:

      # Interactive mode — prompts for everything\n
      python scripts/populate_archive.py

      # One-liner with a new persona\n
      python scripts/populate_archive.py --topic "..." --depth mid --new-user

      # Reuse existing research (search then pick from results)\n
      python scripts/populate_archive.py --topic "..." --depth low
    """
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        raise click.ClickException(
            "ANTHROPIC_API_KEY is not set.\n"
            "  export ANTHROPIC_API_KEY=sk-ant-..."
        )
    anthropic_client = Anthropic(api_key=anthropic_key)

    # ── Gather inputs ──────────────────────────────────────────────────────
    if not topic:
        topic = click.prompt("Research topic")
    if not depth:
        click.echo("Depth options:")
        click.echo("  low   — brief report, 5-10 references")
        click.echo("  mid   — thorough analysis, 10-20 references")
        click.echo("  high  — comprehensive deep dive, 20+ references")
        depth = click.prompt("Depth", type=click.Choice(["low", "mid", "high"]))

    click.echo(f"\n🔍 Searching archive for: {topic!r}")
    matches = _search(topic)

    # ── Reuse flow ─────────────────────────────────────────────────────────
    if matches:
        click.echo(f"\n📚 Found {len(matches)} similar result(s) (≥{int(REUSE_THRESHOLD*100)}% similar):\n")
        for i, m in enumerate(matches, 1):
            pct = int(m["similarity"] * 100)
            quality = f"  quality={m['avg_quality']}" if m.get("avg_quality") else ""
            click.echo(f"  [{i}] {m['title']}")
            click.echo(f"      {pct}% similar · {m['artifact_count']} artifact(s) · {m['reuse_count']} reuse(s){quality}")
            if m.get("synthesized_summary"):
                snippet = m["synthesized_summary"][:120].replace("\n", " ")
                click.echo(f"      > {snippet}…")
            click.echo()

        choices = [str(i) for i in range(1, len(matches) + 1)] + ["n"]
        answer = click.prompt(
            f"Reuse an existing result? Enter 1-{len(matches)} to reuse, or 'n' to research fresh",
            type=click.Choice(choices),
            default="n",
        )
        if answer != "n":
            chosen = matches[int(answer) - 1]
            click.echo(f"\n♻️  Recording reuse for: {chosen['title']}")
            _record_reuse(chosen["canonical_question_id"], n=3)
            base_url = os.environ.get("SIGNAL_ARCHIVE_URL", "https://genai-gurus.com/signal-archive")
            click.echo(f"✅ Done. Reuse count incremented by 3.")
            click.echo(f"   {base_url}/canonical/?id={chosen['canonical_question_id']}")
            return

    # ── Contributor setup ──────────────────────────────────────────────────
    resolved_api_key = api_key or os.environ.get("SIGNAL_ARCHIVE_API_KEY", "")

    if new_user or not resolved_api_key:
        if new_user:
            click.echo("\n👤 Generating a realistic contributor persona…")
            persona = _generate_persona(anthropic_client)
            click.echo(f"   Name:      {persona['display_name']}")
            click.echo(f"   Handle:    @{persona['handle']}")
            click.echo(f"   Specialty: {persona['specialty']}")
        else:
            # Prompt for contributor details
            click.echo("\n No contributor API key found. Create a new contributor.")
            display_name = click.prompt("Display name")
            handle_base = re.sub(r"[^a-z0-9-]", "-", display_name.lower()).strip("-")[:16]
            persona = {
                "display_name": display_name,
                "handle": f"{handle_base}-{secrets.token_hex(3)}",
            }

        click.echo(f"   Registering @{persona['handle']}…")
        resolved_api_key = _register_contributor(persona["handle"], persona["display_name"])
        click.echo(f"   ✅ Registered. API key saved for this session.")
        click.echo(f"      export SIGNAL_ARCHIVE_API_KEY={resolved_api_key}")

    # ── Research generation ────────────────────────────────────────────────
    click.echo(f"\n🧪 Running {depth} research…")
    research = _generate_research(anthropic_client, topic, depth)

    n_refs = len(research.get("citations", []))
    word_count = len(research.get("full_body", "").split())
    click.echo(f"   Generated: {word_count} words, {n_refs} citations")
    click.echo(f"   Q: {research['cleaned_question']}")

    # ── Submission ─────────────────────────────────────────────────────────
    click.echo("\n📤 Submitting to archive…")
    artifact_id = asyncio.run(_submit(resolved_api_key, research, topic))

    base_url = os.environ.get("SIGNAL_ARCHIVE_URL", "https://genai-gurus.com/signal-archive")
    click.echo(f"\n✅ Artifact submitted: {artifact_id}")
    click.echo(f"   {base_url}/search?q={topic.replace(' ', '+')}")


if __name__ == "__main__":
    main()
