#!/usr/bin/env python3
"""
Claude Code Stop hook for Signal Archive.
Fires when Claude finishes responding. Reads the session transcript,
extracts the last user prompt + assistant response, and submits to archive.

Only submits if SIGNAL_ARCHIVE_API_KEY is set. Silent no-op otherwise.
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
MIN_RESPONSE_CHARS = 300  # skip trivial responses


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


def _text_from_content(content) -> str:
    """Normalise Claude's content field — may be str or list of blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    pass  # skip tool output
        return " ".join(parts)
    return ""


def parse_transcript(transcript_path: str) -> tuple[str, str]:
    """Return (last_user_prompt, last_assistant_response) from a JSONL transcript."""
    messages = []
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    # Claude Code transcript format: {"type": "human"|"assistant", "message": {...}}
                    # or flat {"role": "user"|"assistant", "content": "..."}
                    if "message" in obj:
                        msg = obj["message"]
                        role = msg.get("role", obj.get("type", ""))
                    else:
                        msg = obj
                        role = obj.get("role", "")
                    if role in ("user", "human", "assistant"):
                        messages.append({"role": role, "content": _text_from_content(msg.get("content", ""))})
                except json.JSONDecodeError:
                    continue
    except (FileNotFoundError, OSError):
        return "", ""

    last_assistant = ""
    last_user = ""
    for msg in reversed(messages):
        role = msg["role"]
        content = msg["content"].strip()
        if not last_assistant and role == "assistant":
            last_assistant = content
        elif last_assistant and not last_user and role in ("user", "human"):
            last_user = content
            break

    return last_user, last_assistant


async def run_post_hook(prompt: str, result_text: str, model_info: str = None) -> str:
    if not os.environ.get("SIGNAL_ARCHIVE_API_KEY"):
        return ""

    if len(result_text) < MIN_RESPONSE_CHARS:
        return ""

    sanitized = sanitize_prompt(prompt)
    if not sanitized.safe_to_submit:
        return f"Signal Archive: skipped — {sanitized.reason}"

    citations = extract_citations(result_text)
    source_domains = list({c.domain for c in citations})

    payload = ArtifactPayload(
        cleaned_question=sanitized.cleaned_prompt.split("\n")[0][:300],
        cleaned_prompt=sanitized.cleaned_prompt,
        short_answer=_extract_short_answer(result_text),
        full_body=result_text,
        citations=citations,
        run_date=datetime.now(timezone.utc),
        worker_type="claude_code",
        source_domains=source_domains,
        prompt_modified=sanitized.was_modified,
        model_info=model_info,
    )

    client = ArchiveClient()
    artifact_id = await client.submit(payload)
    return f"Signal Archive: contributed to archive (ID: {artifact_id})"


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    # Stop hook: {"session_id": "...", "transcript_path": "..."}
    if "transcript_path" in data:
        prompt, result_text = parse_transcript(data["transcript_path"])
        model_info = None
    else:
        # Fallback: explicit {"prompt": ..., "result": ..., "model": ...}
        prompt = data.get("prompt", "")
        result_text = data.get("result", "")
        model_info = data.get("model")

    if not prompt.strip() or not result_text.strip():
        sys.exit(0)

    output = asyncio.run(run_post_hook(prompt=prompt, result_text=result_text, model_info=model_info))
    if output:
        print(output)


if __name__ == "__main__":
    main()
