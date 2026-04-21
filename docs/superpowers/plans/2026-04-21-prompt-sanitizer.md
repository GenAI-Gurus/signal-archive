# Prompt Sanitizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Python module that sanitizes research prompts before archive submission, using Claude to detect and remove personal, private, or non-public content, returning a structured result that workers can act on.

**Architecture:** A single `sanitizer/` package callable by both the Claude Code and Codex worker integrations. Uses Claude (claude-sonnet-4-6) with a structured JSON response to detect private content categories and rewrite the prompt if needed. Returns a dataclass with the cleaned prompt, a modified flag, and a list of removed categories. Entirely stateless — no database dependency.

**Tech Stack:** Python 3.11, anthropic SDK, pydantic, pytest

**Dependency note:** This plan is independent of the Core Backend plan and can be built in parallel. Workers (Plan 4) import from this package.

---

## File Structure

```
sanitizer/
├── __init__.py          # exports sanitize_prompt
├── client.py            # Anthropic client init
├── prompt.py            # The sanitization prompt template
├── sanitizer.py         # Main sanitize_prompt function
├── models.py            # SanitizationResult dataclass
└── requirements.txt
tests/
└── test_sanitizer.py
```

---

### Task 1: Package scaffold

**Files:**
- Create: `sanitizer/requirements.txt`
- Create: `sanitizer/models.py`
- Create: `sanitizer/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
anthropic==0.40.0
pydantic==2.9.2
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-mock==3.14.0
```

- [ ] **Step 2: Create models.py**

```python
from dataclasses import dataclass, field

@dataclass
class SanitizationResult:
    cleaned_prompt: str
    was_modified: bool
    removed_categories: list[str]    # e.g. ["personal_name", "contact_info"]
    safe_to_submit: bool             # False if prompt can't be cleaned without losing meaning
    reason: str = ""                 # Human-readable explanation shown to user if modified
```

- [ ] **Step 3: Create __init__.py**

```python
from .sanitizer import sanitize_prompt
from .models import SanitizationResult

__all__ = ["sanitize_prompt", "SanitizationResult"]
```

- [ ] **Step 4: Commit**

```bash
git add sanitizer/
git commit -m "feat(sanitizer): package scaffold with SanitizationResult model"
```

---

### Task 2: Anthropic client and system prompt

**Files:**
- Create: `sanitizer/client.py`
- Create: `sanitizer/prompt.py`

- [ ] **Step 1: Create client.py**

```python
import os
import anthropic

def get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=api_key)
```

- [ ] **Step 2: Create prompt.py**

```python
SYSTEM_PROMPT = """You are a research prompt sanitizer for a public research archive.

Your job is to decide whether a research prompt is safe to publish publicly, and if not, clean it.

A prompt is PUBLIC SAFE when it:
- Researches only public information available on the web
- Contains no personal names of private individuals
- Contains no contact information (email, phone, address)
- Contains no references to private company internals, internal documents, or confidential data
- Contains no repository paths, secrets, or credentials
- Contains no personal memory context like "as I mentioned before" or "based on my previous research"
- Contains no content derived from private files or private databases

Detect the following private content categories if present:
- personal_name: real names of private individuals
- contact_info: email, phone, address
- private_company_data: internal company information, unreleased products, internal processes
- private_memory_context: references to personal chat history or personal memory
- private_file_reference: paths to local files, private repos, internal docs
- credentials_or_secrets: API keys, passwords, tokens
- sensitive_identity: health, religion, sexuality, political affiliation of a specific individual

Your response MUST be a JSON object with exactly these fields:
{
  "cleaned_prompt": "<the cleaned version of the prompt, or the original if no changes needed>",
  "was_modified": <true or false>,
  "removed_categories": ["category1", "category2"],
  "safe_to_submit": <true if the cleaned prompt preserves the research intent, false if cleaning would make it meaningless>,
  "reason": "<a single sentence shown to the user explaining what was removed, empty string if not modified>"
}

Rules:
- If the prompt is already public safe, return it unchanged with was_modified=false and removed_categories=[].
- If the prompt contains private content but can be cleaned while preserving the research question, clean it and return was_modified=true.
- If the prompt is so entangled with private context that cleaning would destroy its meaning, return safe_to_submit=false and explain why in reason.
- Preserve the research intent and all public-domain factual content.
- Do not add disclaimers or commentary to the cleaned prompt itself.
- Only return the JSON object. No other text."""
```

- [ ] **Step 3: Commit**

```bash
git add sanitizer/client.py sanitizer/prompt.py
git commit -m "feat(sanitizer): Anthropic client and sanitization system prompt"
```

---

### Task 3: Core sanitize_prompt function

**Files:**
- Create: `sanitizer/sanitizer.py`
- Test: `tests/test_sanitizer.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_sanitizer.py`:

```python
import json
import pytest
from unittest.mock import MagicMock, patch
from sanitizer import sanitize_prompt, SanitizationResult

def _mock_claude_response(payload: dict) -> MagicMock:
    content = MagicMock()
    content.text = json.dumps(payload)
    response = MagicMock()
    response.content = [content]
    return response

def test_clean_prompt_returns_unchanged():
    clean_response = {
        "cleaned_prompt": "What are the best vector databases in 2025?",
        "was_modified": False,
        "removed_categories": [],
        "safe_to_submit": True,
        "reason": ""
    }
    with patch("sanitizer.sanitizer.get_client") as mock_client_fn:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_claude_response(clean_response)
        mock_client_fn.return_value = mock_client

        result = sanitize_prompt("What are the best vector databases in 2025?")

    assert isinstance(result, SanitizationResult)
    assert result.was_modified is False
    assert result.safe_to_submit is True
    assert result.removed_categories == []
    assert "vector databases" in result.cleaned_prompt

def test_personal_name_is_removed():
    dirty_response = {
        "cleaned_prompt": "Research the top AI startups founded in 2023.",
        "was_modified": True,
        "removed_categories": ["personal_name"],
        "safe_to_submit": True,
        "reason": "Removed the personal name of the user."
    }
    with patch("sanitizer.sanitizer.get_client") as mock_client_fn:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_claude_response(dirty_response)
        mock_client_fn.return_value = mock_client

        result = sanitize_prompt("Research the top AI startups founded in 2023 that John Smith mentioned.")

    assert result.was_modified is True
    assert "personal_name" in result.removed_categories
    assert result.safe_to_submit is True
    assert "John Smith" not in result.cleaned_prompt

def test_prompt_too_private_returns_unsafe():
    unsafe_response = {
        "cleaned_prompt": "",
        "was_modified": True,
        "removed_categories": ["private_company_data", "credentials_or_secrets"],
        "safe_to_submit": False,
        "reason": "Prompt relies entirely on confidential company data and cannot be cleaned."
    }
    with patch("sanitizer.sanitizer.get_client") as mock_client_fn:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_claude_response(unsafe_response)
        mock_client_fn.return_value = mock_client

        result = sanitize_prompt("Using our internal Q3 revenue data and AWS_SECRET=abc123, research competitor pricing.")

    assert result.safe_to_submit is False
    assert "credentials_or_secrets" in result.removed_categories

def test_malformed_claude_response_raises():
    with patch("sanitizer.sanitizer.get_client") as mock_client_fn:
        mock_client = MagicMock()
        content = MagicMock()
        content.text = "this is not json"
        mock_client.messages.create.return_value = MagicMock(content=[content])
        mock_client_fn.return_value = mock_client

        with pytest.raises(ValueError, match="Failed to parse sanitizer response"):
            sanitize_prompt("Some prompt")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sanitizer && pip install -r requirements.txt
pytest ../tests/test_sanitizer.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'sanitizer'`

- [ ] **Step 3: Create sanitizer.py**

```python
import json
from .client import get_client
from .prompt import SYSTEM_PROMPT
from .models import SanitizationResult

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

def sanitize_prompt(prompt: str) -> SanitizationResult:
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse sanitizer response: {e}\nRaw: {raw}") from e

    return SanitizationResult(
        cleaned_prompt=data["cleaned_prompt"],
        was_modified=data["was_modified"],
        removed_categories=data.get("removed_categories", []),
        safe_to_submit=data["safe_to_submit"],
        reason=data.get("reason", ""),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest ../tests/test_sanitizer.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add sanitizer/sanitizer.py tests/test_sanitizer.py
git commit -m "feat(sanitizer): core sanitize_prompt function with Claude-based detection"
```

---

### Task 4: Integration smoke test against real Claude API

This task runs once manually to validate the prompt and model work correctly end-to-end before workers depend on the sanitizer.

- [ ] **Step 1: Create tests/test_sanitizer_integration.py**

```python
"""Run with: ANTHROPIC_API_KEY=... pytest tests/test_sanitizer_integration.py -v -m integration"""
import pytest
from sanitizer import sanitize_prompt

pytestmark = pytest.mark.integration

def test_clean_public_prompt_passes_through():
    result = sanitize_prompt(
        "Compare the top 5 vector databases available in 2025 by performance, cost, and scalability."
    )
    assert result.safe_to_submit is True
    assert result.was_modified is False
    assert result.removed_categories == []

def test_personal_name_is_stripped():
    result = sanitize_prompt(
        "Research which AI tools Alice Johnson recommended to her team at Stripe for automating code review."
    )
    assert result.safe_to_submit is True
    assert result.was_modified is True
    assert "personal_name" in result.removed_categories
    assert "Alice Johnson" not in result.cleaned_prompt

def test_credentials_in_prompt_blocks_submission():
    result = sanitize_prompt(
        "Using our database at postgres://admin:SuperSecret123@internal.db.company.com, "
        "research how competitors handle time-series data."
    )
    assert "credentials_or_secrets" in result.removed_categories
```

- [ ] **Step 2: Run integration tests with real API key**

```bash
ANTHROPIC_API_KEY="$(op read 'op://ch-os-priv/anthropic-api-key/credential')" \
  pytest tests/test_sanitizer_integration.py -v -m integration
```

Expected: all 3 tests PASS with real Claude responses

- [ ] **Step 3: Commit**

```bash
git add tests/test_sanitizer_integration.py
git commit -m "test(sanitizer): integration smoke tests against real Claude API"
```

---

### Self-Review

**Spec coverage:**
- ✅ Removes personal names (§13.2.1)
- ✅ Removes contact information (§13.2.2)
- ✅ Removes sensitive identity references (§13.2.3)
- ✅ Removes private memory context (§13.2.4)
- ✅ Removes employer internal context (§13.2.5)
- ✅ Removes private file references (§13.2.6)
- ✅ Removes secrets/credentials (§13.2.7)
- ✅ Returns was_modified flag (§13.4.11)
- ✅ Returns safe_to_submit=False when cleaning would destroy meaning (§13.2 last paragraph)
- ✅ reason field provides user-facing explanation (§13.2 "user must be shown the cleaned version")
- ✅ Stateless — no database dependency

**Placeholder scan:** None found.

**Type consistency:** `SanitizationResult` fields are used consistently in tests and the function implementation.
