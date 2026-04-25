#!/usr/bin/env python3
"""
Codex CLI post-task hook for Signal Archive.
Codex calls this as a shell tool after completing research:
  python3 ~/.signal-archive/codex_integration/hooks/post_task.py \
    --question "..." --body "..." [--model "o4-mini"]
Only submits if SIGNAL_ARCHIVE_API_KEY is set.
"""
import argparse
import asyncio
import json
import re
import sys
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sanitizer import sanitize_prompt
from worker_sdk import ArchiveClient, ArtifactPayload, Citation

URL_PATTERN = re.compile(r'https?://[^\s\)\]\'"<>]+')
SUMMARY_MAX_CHARS = 500
MIN_BODY_CHARS = 300


def extract_citations(text: str) -> list[Citation]:
    seen = set()
    citations = []
    for url in URL_PATTERN.findall(text):
        url = url.rstrip(".,;:!?")
        if url in seen:
            continue
        seen.add(url)
        parsed = urlparse(url)
        domain = parsed.netloc.lstrip("www.")
        citations.append(Citation(url=url, title=url, domain=domain))
    return citations


def _extract_short_answer(text: str) -> str:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and not p.strip().startswith("#")]
    if not paragraphs:
        return text[:SUMMARY_MAX_CHARS]
    return paragraphs[0][:SUMMARY_MAX_CHARS]


async def run_post_hook(question: str, body: str, model_info: str = None) -> str:
    if not os.environ.get("SIGNAL_ARCHIVE_API_KEY"):
        return ""

    if len(body) < MIN_BODY_CHARS:
        return ""

    sanitized = sanitize_prompt(question)
    if not sanitized.safe_to_submit:
        return f"Signal Archive: skipped — {sanitized.reason}"

    citations = extract_citations(body)
    source_domains = list({c.domain for c in citations})

    payload = ArtifactPayload(
        cleaned_question=sanitized.cleaned_prompt.split("\n")[0][:300],
        cleaned_prompt=sanitized.cleaned_prompt,
        short_answer=_extract_short_answer(body),
        full_body=body,
        citations=citations,
        run_date=datetime.now(timezone.utc),
        worker_type="codex",
        source_domains=source_domains,
        prompt_modified=sanitized.was_modified,
        model_info=model_info,
    )

    client = ArchiveClient()
    try:
        artifact_id = await client.submit(payload)
    except Exception as e:
        return f"Signal Archive: submission failed — {e}"
    return f"Signal Archive: contributed to archive (ID: {artifact_id})"


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--question", default="")
    parser.add_argument("--body", default="")
    parser.add_argument("--model", default=None)
    args, _ = parser.parse_known_args()

    question = args.question
    body = args.body
    model_info = args.model

    # Fall back to stdin JSON if CLI args are absent (programmatic use)
    if not question and not body:
        try:
            raw = sys.stdin.read()
            data = json.loads(raw) if raw.strip() else {}
            question = data.get("question", "")
            body = data.get("body", "")
            model_info = data.get("model", model_info)
        except (json.JSONDecodeError, EOFError):
            pass

    if not question.strip() or not body.strip():
        sys.exit(0)

    output = asyncio.run(run_post_hook(question=question, body=body, model_info=model_info))
    if output:
        print(output)


if __name__ == "__main__":
    main()
