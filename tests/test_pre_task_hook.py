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

@pytest.mark.asyncio
async def test_reuse_recorded_for_strong_matches():
    """record_reuse is called once per strong match when results are found."""
    clean_result = SanitizationResult(
        cleaned_prompt="What are the best vector databases in 2025?",
        was_modified=False, removed_categories=[], safe_to_submit=True, reason=""
    )
    matches = [
        SearchMatch(canonical_question_id="cq-1", title="VDB 1", synthesized_summary="s",
                    similarity=0.92, artifact_count=2, reuse_count=5, last_updated_at="2026-01-01"),
        SearchMatch(canonical_question_id="cq-2", title="VDB 2", synthesized_summary="s",
                    similarity=0.85, artifact_count=1, reuse_count=0, last_updated_at="2026-01-01"),
    ]

    with patch("claude_code_integration.hooks.pre_task.sanitize_prompt", return_value=clean_result), \
         patch("claude_code_integration.hooks.pre_task.ArchiveClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=matches)
        mock_client.record_reuse = AsyncMock()
        mock_cls.return_value = mock_client

        await run_hook("What are the best vector databases in 2025?")

    assert mock_client.record_reuse.call_count == 2
    mock_client.record_reuse.assert_any_call("cq-1")
    mock_client.record_reuse.assert_any_call("cq-2")


@pytest.mark.asyncio
async def test_reuse_failure_does_not_break_hook():
    """If record_reuse raises, run_hook still returns output."""
    clean_result = SanitizationResult(
        cleaned_prompt="What is eventual consistency?",
        was_modified=False, removed_categories=[], safe_to_submit=True, reason=""
    )
    matches = [
        SearchMatch(canonical_question_id="cq-99", title="Consistency models",
                    synthesized_summary="s", similarity=0.90, artifact_count=1,
                    reuse_count=0, last_updated_at="2026-01-01"),
    ]

    with patch("claude_code_integration.hooks.pre_task.sanitize_prompt", return_value=clean_result), \
         patch("claude_code_integration.hooks.pre_task.ArchiveClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=matches)
        mock_client.record_reuse = AsyncMock(side_effect=Exception("network error"))
        mock_cls.return_value = mock_client

        output = await run_hook("What is eventual consistency?")

    assert "Signal Archive" in output
