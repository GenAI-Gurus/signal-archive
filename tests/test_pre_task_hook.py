import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sanitizer'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'worker_sdk'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, AsyncMock
from sanitizer import SanitizationResult
from worker_sdk import SearchMatch
from claude_code_integration.hooks.pre_task import run_hook

@pytest.mark.asyncio
async def test_clean_research_prompt_triggers_search():
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
    assert "95%" in output

@pytest.mark.asyncio
async def test_unsafe_prompt_shows_warning():
    unsafe_result = SanitizationResult(
        cleaned_prompt="",
        was_modified=True,
        removed_categories=["credentials_or_secrets"],
        safe_to_submit=False,
        reason="Prompt contains credentials and cannot be safely archived."
    )

    with patch("claude_code_integration.hooks.pre_task.sanitize_prompt", return_value=unsafe_result):
        output = await run_hook("Research using our db at postgres://admin:pw@host, compare competitors.")

    assert "not archivable" in output.lower()

@pytest.mark.asyncio
async def test_modified_prompt_shows_cleaned_version():
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
    assert "Research the top AI startups founded in 2023." in output
