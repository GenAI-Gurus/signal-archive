#!/usr/bin/env python3
"""
Codex CLI pre-task hook for Signal Archive.
Codex calls this as a shell tool before starting research:
  python3 ~/.signal-archive/codex_integration/hooks/pre_task.py "research question"
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sanitizer import sanitize_prompt, SanitizationResult
from worker_sdk import ArchiveClient, SearchMatch

SIMILARITY_THRESHOLD = 0.80


def _format_search_results(matches: list[SearchMatch]) -> str:
    if not matches:
        return "Signal Archive: No similar research found. This appears to be fresh research territory."
    lines = ["**Signal Archive — Existing Research Found:**\n"]
    base_url = os.environ.get("SIGNAL_ARCHIVE_URL", "https://genai-gurus.com/signal-archive")
    for i, m in enumerate(matches, 1):
        pct = int(m.similarity * 100)
        lines.append(f"{i}. [{m.title}]({base_url}/canonical/?id={m.canonical_question_id})")
        if m.synthesized_summary:
            lines.append(f"   > {m.synthesized_summary[:150]}...")
        lines.append(f"   Similarity: {pct}% | Artifacts: {m.artifact_count} | Reused: {m.reuse_count}x\n")
    lines.append("Consider reusing an existing result or proceed with a new run. New runs are automatically contributed to the archive.")
    return "\n".join(lines)


async def run_hook(prompt: str) -> str:
    result: SanitizationResult = sanitize_prompt(prompt)

    if not result.safe_to_submit:
        return (
            f"Signal Archive: This prompt is not archivable.\n"
            f"Reason: {result.reason}\n"
            f"Research will run normally but will not be contributed to the public archive."
        )

    output_parts = []

    if result.was_modified:
        output_parts.append(
            f"Signal Archive — Prompt cleaned for public archive:\n"
            f"Removed: {', '.join(result.removed_categories)}\n"
            f"Reason: {result.reason}\n\n"
            f"Cleaned prompt:\n> {result.cleaned_prompt}\n"
        )

    client = ArchiveClient()
    matches = await client.search(result.cleaned_prompt, limit=3)
    strong_matches = [m for m in matches if m.similarity >= SIMILARITY_THRESHOLD]

    for m in strong_matches:
        try:
            await client.record_reuse(m.canonical_question_id)
        except Exception:
            pass

    output_parts.append(_format_search_results(strong_matches))
    return "\n".join(output_parts)


def main():
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        try:
            raw = sys.stdin.read()
            data = json.loads(raw) if raw.strip() else {}
            prompt = data.get("prompt", raw)
        except (json.JSONDecodeError, EOFError):
            prompt = ""

    if not prompt.strip():
        sys.exit(0)

    output = asyncio.run(run_hook(prompt))
    print(output)


if __name__ == "__main__":
    main()
