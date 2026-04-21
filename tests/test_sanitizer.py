import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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
