import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, AsyncMock
from sanitizer import SanitizationResult
from worker_sdk import SearchMatch
from codex_integration.hooks.pre_task import run_hook


@pytest.mark.asyncio
async def test_clean_prompt_returns_search_results():
    clean = SanitizationResult(
        cleaned_prompt="What are the best vector databases for AI workloads?",
        was_modified=False, removed_categories=[], safe_to_submit=True, reason=""
    )
    matches = [SearchMatch(
        canonical_question_id="cq-1",
        title="Best vector databases for AI",
        synthesized_summary="Pinecone, Weaviate, and pgvector are top choices.",
        similarity=0.92, artifact_count=3, reuse_count=7,
        last_updated_at="2026-04-01T00:00:00"
    )]
    with patch("codex_integration.hooks.pre_task.sanitize_prompt", return_value=clean), \
         patch("codex_integration.hooks.pre_task.ArchiveClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=matches)
        mock_client.record_reuse = AsyncMock()
        mock_cls.return_value = mock_client
        output = await run_hook("What are the best vector databases for AI workloads?")
    assert "Signal Archive" in output
    assert "Best vector databases for AI" in output
    assert "92%" in output


@pytest.mark.asyncio
async def test_unsafe_prompt_returns_warning_without_search():
    unsafe = SanitizationResult(
        cleaned_prompt="", was_modified=True,
        removed_categories=["credentials_or_secrets"], safe_to_submit=False,
        reason="Prompt contains credentials."
    )
    with patch("codex_integration.hooks.pre_task.sanitize_prompt", return_value=unsafe), \
         patch("codex_integration.hooks.pre_task.ArchiveClient") as mock_cls:
        output = await run_hook("Connect to postgres://admin:secret@host and research competitors.")
    assert "not archivable" in output.lower()
    mock_cls.assert_not_called()


@pytest.mark.asyncio
async def test_modified_prompt_shows_cleaned_version():
    modified = SanitizationResult(
        cleaned_prompt="Research the top AI startups founded in 2023.",
        was_modified=True, removed_categories=["personal_name"], safe_to_submit=True,
        reason="Removed personal name."
    )
    with patch("codex_integration.hooks.pre_task.sanitize_prompt", return_value=modified), \
         patch("codex_integration.hooks.pre_task.ArchiveClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=[])
        mock_client.record_reuse = AsyncMock()
        mock_cls.return_value = mock_client
        output = await run_hook("Research top AI startups John Smith mentioned.")
    assert "Research the top AI startups founded in 2023." in output
    assert "cleaned" in output.lower() or "removed" in output.lower()


@pytest.mark.asyncio
async def test_reuse_recorded_for_strong_matches():
    clean = SanitizationResult(
        cleaned_prompt="Rust vs Go for CLI tools?",
        was_modified=False, removed_categories=[], safe_to_submit=True, reason=""
    )
    matches = [
        SearchMatch(canonical_question_id="cq-1", title="Rust vs Go CLI",
                    synthesized_summary="s", similarity=0.91, artifact_count=2,
                    reuse_count=4, last_updated_at="2026-01-01"),
        SearchMatch(canonical_question_id="cq-2", title="Go CLI tools",
                    synthesized_summary="s", similarity=0.83, artifact_count=1,
                    reuse_count=1, last_updated_at="2026-01-01"),
    ]
    with patch("codex_integration.hooks.pre_task.sanitize_prompt", return_value=clean), \
         patch("codex_integration.hooks.pre_task.ArchiveClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=matches)
        mock_client.record_reuse = AsyncMock()
        mock_cls.return_value = mock_client
        await run_hook("Rust vs Go for CLI tools?")
    assert mock_client.record_reuse.call_count == 2
    mock_client.record_reuse.assert_any_call("cq-1")
    mock_client.record_reuse.assert_any_call("cq-2")


@pytest.mark.asyncio
async def test_no_results_returns_fresh_territory_message():
    clean = SanitizationResult(
        cleaned_prompt="Obscure niche research topic 2026",
        was_modified=False, removed_categories=[], safe_to_submit=True, reason=""
    )
    with patch("codex_integration.hooks.pre_task.sanitize_prompt", return_value=clean), \
         patch("codex_integration.hooks.pre_task.ArchiveClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=[])
        mock_client.record_reuse = AsyncMock()
        mock_cls.return_value = mock_client
        output = await run_hook("Obscure niche research topic 2026")
    assert "no similar" in output.lower() or "fresh" in output.lower()


@pytest.mark.asyncio
async def test_reuse_failure_does_not_break_hook():
    clean = SanitizationResult(
        cleaned_prompt="What is eventual consistency?",
        was_modified=False, removed_categories=[], safe_to_submit=True, reason=""
    )
    matches = [SearchMatch(canonical_question_id="cq-99", title="Consistency models",
                           synthesized_summary="s", similarity=0.90, artifact_count=1,
                           reuse_count=0, last_updated_at="2026-01-01")]
    with patch("codex_integration.hooks.pre_task.sanitize_prompt", return_value=clean), \
         patch("codex_integration.hooks.pre_task.ArchiveClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=matches)
        mock_client.record_reuse = AsyncMock(side_effect=Exception("network error"))
        mock_cls.return_value = mock_client
        output = await run_hook("What is eventual consistency?")
    assert "Signal Archive" in output
