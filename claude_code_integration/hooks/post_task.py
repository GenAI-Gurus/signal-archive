#!/usr/bin/env python3
"""
Claude Code post-task hook for Signal Archive.
Called after a research task completes.
Extracts citations, sanitizes prompt, submits artifact to archive.
"""
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

async def run_post_hook(
    prompt: str,
    result_text: str,
    worker_type: str = "claude_code",
    model_info: str = None,
) -> str:
    sanitized = sanitize_prompt(prompt)

    if not sanitized.safe_to_submit:
        return f"Signal Archive: skipped submission — {sanitized.reason}"

    citations = extract_citations(result_text)
    source_domains = list({c.domain for c in citations})

    payload = ArtifactPayload(
        cleaned_question=sanitized.cleaned_prompt.split("\n")[0][:300],
        cleaned_prompt=sanitized.cleaned_prompt,
        short_answer=_extract_short_answer(result_text),
        full_body=result_text,
        citations=citations,
        run_date=datetime.now(timezone.utc),
        worker_type=worker_type,
        source_domains=source_domains,
        prompt_modified=sanitized.was_modified,
        model_info=model_info,
    )

    client = ArchiveClient()
    artifact_id = await client.submit(payload)
    return f"Signal Archive: artifact submitted (ID: {artifact_id})"

def main():
    try:
        data = json.loads(sys.stdin.read())
        prompt = data.get("prompt", "")
        result_text = data.get("result", "")
        model_info = data.get("model", None)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    if not prompt.strip() or not result_text.strip():
        sys.exit(0)

    output = asyncio.run(run_post_hook(prompt=prompt, result_text=result_text, model_info=model_info))
    print(output)

if __name__ == "__main__":
    main()
