# Worker Integrations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Claude Code and Codex worker integrations that automatically intercept research tasks, sanitize prompts, search the archive before running, and auto-submit cleaned artifacts after a completed run.

**Architecture:** Two separate integrations sharing a common `worker_sdk/` Python package. The Claude Code integration uses Claude Code hooks (pre-task + post-task) configured in `.claude/settings.json`. The Codex integration uses a Codex plugin. Both use the sanitizer package and call the Signal Archive API. The SDK handles API calls, the hooks/plugins handle the lifecycle.

**Tech Stack:** Python 3.11, httpx (async HTTP), anthropic SDK (for sanitizer), Claude Code hooks, Codex plugin system

**Dependencies:** Core Backend (Plan 1) must be deployed. Prompt Sanitizer (Plan 2) must be complete.

---

## File Structure

```
worker_sdk/
├── __init__.py              # exports search_archive, submit_artifact, sanitize
├── api.py                   # Signal Archive API client
├── models.py                # Shared data models
└── requirements.txt

claude_code_integration/
├── hooks/
│   ├── pre_task.py          # Runs before task: sanitize + search
│   └── post_task.py         # Runs after task: extract + submit
├── skill/
│   └── signal-archive.md   # Claude Code skill for /signal-archive command
└── setup.py                 # Installs hooks into .claude/settings.json

tests/
├── test_worker_sdk.py
├── test_pre_task_hook.py
└── test_post_task_hook.py
```

---

### Task 1: Worker SDK — API client

**Files:**
- Create: `worker_sdk/requirements.txt`
- Create: `worker_sdk/models.py`
- Create: `worker_sdk/api.py`
- Create: `worker_sdk/__init__.py`

- [ ] **Step 1: Create worker_sdk/requirements.txt**

```
httpx==0.27.2
pydantic==2.9.2
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-mock==3.14.0
```

- [ ] **Step 2: Create worker_sdk/models.py**

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Citation:
    url: str
    title: str
    domain: str

@dataclass
class SearchMatch:
    canonical_question_id: str
    title: str
    synthesized_summary: Optional[str]
    similarity: float
    artifact_count: int
    reuse_count: int
    last_updated_at: str

@dataclass
class ArtifactPayload:
    cleaned_question: str
    cleaned_prompt: str
    short_answer: str
    full_body: str
    citations: list[Citation]
    run_date: datetime
    worker_type: str                  # 'claude_code' | 'codex'
    source_domains: list[str]
    prompt_modified: bool
    clarifying_qa: list[dict] = field(default_factory=list)
    model_info: Optional[str] = None
    version: Optional[str] = None
```

- [ ] **Step 3: Create worker_sdk/api.py**

```python
import os
import httpx
from .models import SearchMatch, ArtifactPayload

class ArchiveClient:
    def __init__(self):
        self.base_url = os.environ.get("SIGNAL_ARCHIVE_API_URL", "https://signal-archive-api.fly.dev")
        self.api_key = os.environ.get("SIGNAL_ARCHIVE_API_KEY", "")

    async def search(self, query: str, limit: int = 5) -> list[SearchMatch]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/search",
                params={"q": query, "limit": limit},
            )
            response.raise_for_status()
        return [SearchMatch(**item) for item in response.json()]

    async def submit(self, payload: ArtifactPayload) -> str:
        """Submit artifact. Returns artifact_id."""
        body = {
            "cleaned_question": payload.cleaned_question,
            "cleaned_prompt": payload.cleaned_prompt,
            "clarifying_qa": payload.clarifying_qa,
            "short_answer": payload.short_answer,
            "full_body": payload.full_body,
            "citations": [{"url": c.url, "title": c.title, "domain": c.domain} for c in payload.citations],
            "run_date": payload.run_date.isoformat(),
            "worker_type": payload.worker_type,
            "model_info": payload.model_info,
            "source_domains": payload.source_domains,
            "prompt_modified": payload.prompt_modified,
            "version": payload.version,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/artifacts",
                json=body,
                headers={"X-API-Key": self.api_key},
            )
            response.raise_for_status()
        return response.json()["id"]

    async def record_reuse(self, canonical_question_id: str) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{self.base_url}/canonical/{canonical_question_id}/reuse",
                params={"reused_by": "claude_code"},
            )
```

- [ ] **Step 4: Create worker_sdk/__init__.py**

```python
from .api import ArchiveClient
from .models import SearchMatch, ArtifactPayload, Citation

__all__ = ["ArchiveClient", "SearchMatch", "ArtifactPayload", "Citation"]
```

- [ ] **Step 5: Write and run tests for the API client**

Create `tests/test_worker_sdk.py`:

```python
import pytest
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from worker_sdk import ArchiveClient, SearchMatch

@pytest.mark.asyncio
async def test_search_returns_match_list():
    fake_results = [{
        "canonical_question_id": "cq-id-1",
        "title": "Best vector databases 2025",
        "synthesized_summary": "Overview of top vector DBs",
        "similarity": 0.94,
        "artifact_count": 3,
        "reuse_count": 7,
        "last_updated_at": "2026-04-01T00:00:00"
    }]
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.json.return_value = fake_results
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        client = ArchiveClient()
        results = await client.search("best vector databases")

    assert len(results) == 1
    assert isinstance(results[0], SearchMatch)
    assert results[0].similarity == 0.94

@pytest.mark.asyncio
async def test_search_returns_empty_on_no_results():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        client = ArchiveClient()
        results = await client.search("very obscure topic with no matches")

    assert results == []
```

```bash
cd worker_sdk && pip install -r requirements.txt
pytest ../tests/test_worker_sdk.py -v
```

Expected: both tests PASS

- [ ] **Step 6: Commit**

```bash
git add worker_sdk/ tests/test_worker_sdk.py
git commit -m "feat(workers): worker SDK with ArchiveClient for search and submit"
```

---

### Task 2: Pre-task hook — sanitize and search

**Files:**
- Create: `claude_code_integration/hooks/pre_task.py`
- Test: `tests/test_pre_task_hook.py`

The pre-task hook is called by Claude Code before starting a task. It receives the task prompt via stdin as JSON, sanitizes it, searches the archive, and prints a formatted result to stdout for Claude Code to surface to the user.

- [ ] **Step 1: Write failing tests**

Create `tests/test_pre_task_hook.py`:

```python
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import sys
import io

# We test the hook's main() function directly
from claude_code_integration.hooks.pre_task import run_hook

@pytest.mark.asyncio
async def test_clean_research_prompt_triggers_search():
    from sanitizer import SanitizationResult
    from worker_sdk import SearchMatch

    clean_result = SanitizationResult(
        cleaned_prompt="What are the best vector databases in 2025?",
        was_modified=False,
        removed_categories=[],
        safe_to_submit=True,
        reason=""
    )
    search_matches = [SearchMatch(
        canonical_question_id="cq-1",
        title="Best vector databases 2025",
        synthesized_summary="Top options include Pinecone, Weaviate, pgvector",
        similarity=0.95,
        artifact_count=3,
        reuse_count=12,
        last_updated_at="2026-04-01T00:00:00"
    )]

    with patch("claude_code_integration.hooks.pre_task.sanitize_prompt", return_value=clean_result), \
         patch("claude_code_integration.hooks.pre_task.ArchiveClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=search_matches)
        mock_client_cls.return_value = mock_client

        output = await run_hook("What are the best vector databases in 2025?")

    assert "Signal Archive" in output
    assert "Best vector databases 2025" in output
    assert "0.95" in output or "95%" in output

@pytest.mark.asyncio
async def test_unsafe_prompt_shows_warning():
    from sanitizer import SanitizationResult

    unsafe_result = SanitizationResult(
        cleaned_prompt="",
        was_modified=True,
        removed_categories=["credentials_or_secrets"],
        safe_to_submit=False,
        reason="Prompt contains credentials and cannot be safely archived."
    )

    with patch("claude_code_integration.hooks.pre_task.sanitize_prompt", return_value=unsafe_result):
        output = await run_hook("Research using our db at postgres://admin:pw@host, compare competitors.")

    assert "not archivable" in output.lower() or "cannot be archived" in output.lower()

@pytest.mark.asyncio
async def test_modified_prompt_shows_cleaned_version():
    from sanitizer import SanitizationResult

    modified_result = SanitizationResult(
        cleaned_prompt="Research the top AI startups founded in 2023.",
        was_modified=True,
        removed_categories=["personal_name"],
        safe_to_submit=True,
        reason="Removed personal name from the prompt."
    )

    with patch("claude_code_integration.hooks.pre_task.sanitize_prompt", return_value=modified_result), \
         patch("claude_code_integration.hooks.pre_task.ArchiveClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=[])
        mock_client_cls.return_value = mock_client

        output = await run_hook("Research top AI startups John Smith mentioned in 2023.")

    assert "cleaned" in output.lower() or "modified" in output.lower()
    assert "Research the top AI startups founded in 2023" in output
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_pre_task_hook.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create claude_code_integration/hooks/pre_task.py**

```python
#!/usr/bin/env python3
"""
Claude Code pre-task hook for Signal Archive.
Called before Claude Code starts a task.
Input: task prompt as first argument or via stdin JSON {"prompt": "..."}
Output: formatted message printed to stdout (shown to user by Claude Code)
"""
import asyncio
import json
import sys
import os

# Allow importing from sibling packages
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sanitizer"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "worker_sdk"))

from sanitizer import sanitize_prompt, SanitizationResult
from worker_sdk import ArchiveClient, SearchMatch

SIMILARITY_THRESHOLD_DISPLAY = 0.80  # Only show results above this similarity

def _format_search_results(matches: list[SearchMatch]) -> str:
    if not matches:
        return "No similar research found in the archive. This will be a fresh run."
    lines = ["**Signal Archive — Existing Research Found:**\n"]
    for i, m in enumerate(matches, 1):
        pct = int(m.similarity * 100)
        lines.append(f"{i}. [{m.title}]({os.environ.get('SIGNAL_ARCHIVE_URL', 'https://signal-archive.github.io')}/canonical/{m.canonical_question_id})")
        if m.synthesized_summary:
            lines.append(f"   > {m.synthesized_summary[:150]}...")
        lines.append(f"   Similarity: {pct}% | Artifacts: {m.artifact_count} | Reused: {m.reuse_count}x\n")
    lines.append("You can reuse an existing result or continue with a new run. New runs are automatically contributed to the archive.")
    return "\n".join(lines)

async def run_hook(prompt: str) -> str:
    # Step 1: Sanitize
    result: SanitizationResult = sanitize_prompt(prompt)

    if not result.safe_to_submit:
        return (
            f"⚠️ **Signal Archive: This prompt is not archivable.**\n"
            f"Reason: {result.reason}\n"
            f"The research will run normally but will not be contributed to the public archive."
        )

    output_parts = []

    if result.was_modified:
        output_parts.append(
            f"🧹 **Signal Archive — Prompt cleaned for public archive:**\n"
            f"Removed: {', '.join(result.removed_categories)}\n"
            f"Reason: {result.reason}\n\n"
            f"**Cleaned prompt:**\n> {result.cleaned_prompt}\n"
        )

    # Step 2: Search
    client = ArchiveClient()
    matches = await client.search(result.cleaned_prompt, limit=3)
    strong_matches = [m for m in matches if m.similarity >= SIMILARITY_THRESHOLD_DISPLAY]
    output_parts.append(_format_search_results(strong_matches))

    return "\n".join(output_parts)

def main():
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        try:
            data = json.loads(sys.stdin.read())
            prompt = data.get("prompt", "")
        except (json.JSONDecodeError, EOFError):
            prompt = sys.stdin.read()

    if not prompt.strip():
        sys.exit(0)

    output = asyncio.run(run_hook(prompt))
    print(output)

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create `claude_code_integration/__init__.py` and `claude_code_integration/hooks/__init__.py`**

Both are empty files.

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_pre_task_hook.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add claude_code_integration/ tests/test_pre_task_hook.py
git commit -m "feat(workers): Claude Code pre-task hook — sanitize and search archive"
```

---

### Task 3: Post-task hook — extract and submit artifact

**Files:**
- Create: `claude_code_integration/hooks/post_task.py`
- Test: `tests/test_post_task_hook.py`

The post-task hook is called by Claude Code after a task completes. It receives the task result and submits a cleaned artifact to the archive.

- [ ] **Step 1: Write failing tests**

Create `tests/test_post_task_hook.py`:

```python
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from claude_code_integration.hooks.post_task import run_post_hook, extract_citations

def test_extract_citations_finds_urls():
    text = """
    According to [OpenAI blog](https://openai.com/blog/gpt4) and Anthropic's research
    at https://anthropic.com/research/scaling the models show improvement.
    See also: https://huggingface.co/blog/rlhf for RLHF details.
    """
    citations = extract_citations(text)
    urls = [c.url for c in citations]
    assert "https://openai.com/blog/gpt4" in urls
    assert "https://anthropic.com/research/scaling" in urls
    assert "https://huggingface.co/blog/rlhf" in urls
    for c in citations:
        assert c.domain != ""

@pytest.mark.asyncio
async def test_successful_submission_returns_artifact_id():
    from sanitizer import SanitizationResult
    from worker_sdk import SearchMatch

    clean_result = SanitizationResult(
        cleaned_prompt="What are the top vector databases in 2025?",
        was_modified=False,
        removed_categories=[],
        safe_to_submit=True,
        reason=""
    )

    with patch("claude_code_integration.hooks.post_task.sanitize_prompt", return_value=clean_result), \
         patch("claude_code_integration.hooks.post_task.ArchiveClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.submit = AsyncMock(return_value="artifact-id-123")
        mock_client_cls.return_value = mock_client

        output = await run_post_hook(
            prompt="What are the top vector databases in 2025?",
            result_text="## Vector Database Comparison\n\nPinecone leads with https://pinecone.io/docs...",
            worker_type="claude_code",
        )

    assert "artifact-id-123" in output or "submitted" in output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_post_task_hook.py -v
```

Expected: FAIL

- [ ] **Step 3: Create claude_code_integration/hooks/post_task.py**

```python
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sanitizer"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "worker_sdk"))

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
    """Return first substantive paragraph as short answer, max 500 chars."""
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
    return f"✅ Signal Archive: artifact submitted (ID: {artifact_id})"

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_post_task_hook.py -v
```

Expected: both tests PASS

- [ ] **Step 5: Commit**

```bash
git add claude_code_integration/hooks/post_task.py tests/test_post_task_hook.py
git commit -m "feat(workers): Claude Code post-task hook — extract citations and submit artifact"
```

---

### Task 4: Claude Code settings.json hook wiring

**Files:**
- Create: `claude_code_integration/setup.py`
- Create: `claude_code_integration/skill/signal-archive.md`

- [ ] **Step 1: Create the skill file**

Create `claude_code_integration/skill/signal-archive.md`:

```markdown
# Signal Archive

Search the Signal Archive for existing research before running a new task.

## Usage

`/signal-archive <research question>`

## Behavior

1. Sanitizes the research question to remove any private content
2. Searches the public Signal Archive for similar existing research
3. Presents matching canonical pages with similarity scores and reuse counts
4. If you proceed with the task, the result is automatically contributed to the archive

## Setup

Set `SIGNAL_ARCHIVE_API_KEY` and `SIGNAL_ARCHIVE_API_URL` environment variables.
```

- [ ] **Step 2: Create setup.py to wire hooks into .claude/settings.json**

```python
#!/usr/bin/env python3
"""
Installs Signal Archive hooks into the Claude Code project settings.
Run from the project root: python claude_code_integration/setup.py
"""
import json
import os
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).parent / "hooks"

def main():
    settings_path = Path(".claude/settings.json")
    settings_path.parent.mkdir(exist_ok=True)

    if settings_path.exists():
        with open(settings_path) as f:
            settings = json.load(f)
    else:
        settings = {}

    pre_hook_cmd = f"python {HOOKS_DIR}/pre_task.py"
    post_hook_cmd = f"python {HOOKS_DIR}/post_task.py"

    settings.setdefault("hooks", {})

    # Pre-task hook: runs before Claude starts working
    settings["hooks"]["PreToolUse"] = settings["hooks"].get("PreToolUse", [])
    pre_hook_entry = {"matcher": "Task", "hooks": [{"type": "command", "command": pre_hook_cmd}]}
    if pre_hook_entry not in settings["hooks"]["PreToolUse"]:
        settings["hooks"]["PreToolUse"].append(pre_hook_entry)

    # Post-task hook: runs after task completes
    settings["hooks"]["PostToolUse"] = settings["hooks"].get("PostToolUse", [])
    post_hook_entry = {"matcher": "Task", "hooks": [{"type": "command", "command": post_hook_cmd}]}
    if post_hook_entry not in settings["hooks"]["PostToolUse"]:
        settings["hooks"]["PostToolUse"].append(post_hook_entry)

    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)

    print(f"✅ Signal Archive hooks installed in {settings_path}")
    print(f"   Pre-task: {pre_hook_cmd}")
    print(f"   Post-task: {post_hook_cmd}")
    print(f"\nSet these env vars before running Claude Code:")
    print(f"   SIGNAL_ARCHIVE_API_KEY=<your key from POST /contributors>")
    print(f"   SIGNAL_ARCHIVE_API_URL=https://signal-archive-api.fly.dev")
    print(f"   ANTHROPIC_API_KEY=<your key for sanitizer>")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run setup and verify settings.json is updated**

```bash
python claude_code_integration/setup.py
cat .claude/settings.json
```

Expected: settings.json contains `PreToolUse` and `PostToolUse` hook entries pointing to the hook scripts

- [ ] **Step 4: Smoke test the pre-task hook manually**

```bash
ANTHROPIC_API_KEY="$(op read 'op://ch-os-priv/anthropic-api-key/credential')" \
SIGNAL_ARCHIVE_API_URL="https://signal-archive-api.fly.dev" \
python claude_code_integration/hooks/pre_task.py "What are the best vector databases in 2025?"
```

Expected: output includes "Signal Archive" header and either search results or "No similar research found"

- [ ] **Step 5: Commit**

```bash
git add claude_code_integration/setup.py claude_code_integration/skill/
git commit -m "feat(workers): Claude Code hook wiring and /signal-archive skill"
```

---

### Self-Review

**Spec coverage:**
- ✅ Intercept research task before execution (§10.1.1) — via PreToolUse hook
- ✅ Sanitize prompt before archive mode (§10.1.2, §13.2)
- ✅ Show cleaned prompt if materially modified (§10.1.3, §13.2)
- ✅ Search archive before running (§10.1.4, §13.3)
- ✅ Present relevant existing artifacts (§10.1.5, §13.3)
- ✅ Auto-submit cleaned artifact after completion (§10.1.6, §13.4)
- ✅ Extract citations from result text (§13.4.6)
- ✅ Record worker_type and model_info (§13.4.8, §13.4.9)
- ✅ Set prompt_modified flag (§13.4.11)
- ⚠️ Codex integration is deferred — this plan covers Claude Code only. Codex uses a different plugin API and should be planned separately once the Claude Code integration is validated in production.

**Placeholder scan:** None found.

**Type consistency:** `Citation`, `ArtifactPayload`, `SearchMatch` defined in `worker_sdk/models.py` and used consistently in both hooks.
