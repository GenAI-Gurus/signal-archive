import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
import pytest
from unittest.mock import MagicMock, patch
from sanitizer import sanitize_prompt, SanitizationResult

def _mock_subprocess(payload: dict) -> MagicMock:
    result = MagicMock()
    result.returncode = 0
    result.stdout = json.dumps(payload)
    result.stderr = ""
    return result

def test_clean_prompt_returns_unchanged():
    payload = {
        "cleaned_prompt": "What are the best vector databases in 2025?",
        "was_modified": False,
        "removed_categories": [],
        "safe_to_submit": True,
        "reason": ""
    }
    with patch("sanitizer.sanitizer.detect_cli", return_value="claude"), \
         patch("sanitizer.sanitizer.subprocess.run", return_value=_mock_subprocess(payload)):
        result = sanitize_prompt("What are the best vector databases in 2025?")

    assert isinstance(result, SanitizationResult)
    assert result.was_modified is False
    assert result.safe_to_submit is True
    assert result.removed_categories == []
    assert "vector databases" in result.cleaned_prompt

def test_personal_name_is_removed():
    payload = {
        "cleaned_prompt": "Research the top AI startups founded in 2023.",
        "was_modified": True,
        "removed_categories": ["private_individual"],
        "safe_to_submit": True,
        "reason": "Removed the name of a private individual."
    }
    with patch("sanitizer.sanitizer.detect_cli", return_value="claude"), \
         patch("sanitizer.sanitizer.subprocess.run", return_value=_mock_subprocess(payload)):
        result = sanitize_prompt("Research the top AI startups John Smith mentioned in 2023.")

    assert result.was_modified is True
    assert "private_individual" in result.removed_categories
    assert result.safe_to_submit is True
    assert "John Smith" not in result.cleaned_prompt

def test_prompt_too_private_returns_unsafe():
    payload = {
        "cleaned_prompt": "",
        "was_modified": True,
        "removed_categories": ["implicit_org_reference", "credentials_or_secrets"],
        "safe_to_submit": False,
        "reason": "Prompt relies on private company context and credentials that cannot be removed without losing meaning."
    }
    with patch("sanitizer.sanitizer.detect_cli", return_value="claude"), \
         patch("sanitizer.sanitizer.subprocess.run", return_value=_mock_subprocess(payload)):
        result = sanitize_prompt("Using our internal Q3 revenue data and AWS_SECRET=abc123, research competitor pricing.")

    assert result.safe_to_submit is False
    assert "credentials_or_secrets" in result.removed_categories

def test_malformed_response_raises():
    bad = MagicMock()
    bad.returncode = 0
    bad.stdout = "this is not json"
    bad.stderr = ""
    with patch("sanitizer.sanitizer.detect_cli", return_value="claude"), \
         patch("sanitizer.sanitizer.subprocess.run", return_value=bad):
        with pytest.raises(ValueError, match="Failed to parse sanitizer response"):
            sanitize_prompt("Some prompt")

def test_cli_not_found_raises():
    with patch("sanitizer.sanitizer.detect_cli", side_effect=EnvironmentError("Neither 'claude' nor 'codex' CLI found")):
        with pytest.raises(EnvironmentError, match="claude"):
            sanitize_prompt("Some prompt")
