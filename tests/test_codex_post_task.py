import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, AsyncMock
from sanitizer import SanitizationResult
from codex_integration.hooks.post_task import run_post_hook, extract_citations


def test_extract_citations_finds_urls():
    text = (
        "According to https://openai.com/research/gpt4 and "
        "https://anthropic.com/scaling the results show improvement. "
        "See https://huggingface.co/blog/rlhf for details."
    )
    citations = extract_citations(text)
    urls = [c.url for c in citations]
    assert "https://openai.com/research/gpt4" in urls
    assert "https://anthropic.com/scaling" in urls
    assert "https://huggingface.co/blog/rlhf" in urls
    for c in citations:
        assert c.domain != ""


def test_extract_citations_deduplicates():
    text = "See https://example.com/page and also https://example.com/page again."
    citations = extract_citations(text)
    assert len([c for c in citations if c.url == "https://example.com/page"]) == 1


@pytest.mark.asyncio
async def test_successful_submission_returns_artifact_id():
    clean = SanitizationResult(
        cleaned_prompt="What are the top vector databases in 2025?",
        was_modified=False, removed_categories=[], safe_to_submit=True, reason=""
    )
    with patch("codex_integration.hooks.post_task.sanitize_prompt", return_value=clean), \
         patch("codex_integration.hooks.post_task.ArchiveClient") as mock_cls, \
         patch.dict(os.environ, {"SIGNAL_ARCHIVE_API_KEY": "test-key"}):
        mock_client = AsyncMock()
        mock_client.submit = AsyncMock(return_value="artifact-abc123")
        mock_cls.return_value = mock_client
        output = await run_post_hook(
            question="What are the top vector databases in 2025?",
            body="## Vector Database Comparison\n\nPinecone leads with https://pinecone.io/docs offering low latency and high throughput. "
                 "Weaviate at https://weaviate.io is open source and provides excellent semantic search. pgvector https://github.com/pgvector "
                 "integrates directly with Postgres making it ideal for existing infrastructure. Compared across latency, cost, and ecosystem support, "
                 "each has distinct advantages for different workloads. Pinecone excels at scale, Weaviate at flexibility, and pgvector at simplicity.",
        )
    assert "artifact-abc123" in output
    assert mock_client.submit.call_count == 1
    call_payload = mock_client.submit.call_args[0][0]
    assert call_payload.worker_type == "codex"


@pytest.mark.asyncio
async def test_missing_api_key_is_silent_noop():
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("SIGNAL_ARCHIVE_API_KEY", None)
        output = await run_post_hook(
            question="What are the tradeoffs of Rust vs Go?",
            body="## Rust vs Go\n\nRust offers memory safety. Go offers simple concurrency. "
                 "Both are excellent for systems programming with distinct tradeoffs. "
                 "Performance benchmarks at https://benchmarks.com show close results.",
        )
    assert output == ""


@pytest.mark.asyncio
async def test_short_body_is_skipped():
    with patch.dict(os.environ, {"SIGNAL_ARCHIVE_API_KEY": "test-key"}):
        output = await run_post_hook(question="What is X?", body="Short answer.")
    assert output == ""


@pytest.mark.asyncio
async def test_unsafe_prompt_is_skipped_with_message():
    unsafe = SanitizationResult(
        cleaned_prompt="", was_modified=True,
        removed_categories=["credentials_or_secrets"], safe_to_submit=False,
        reason="Prompt contains secrets."
    )
    with patch("codex_integration.hooks.post_task.sanitize_prompt", return_value=unsafe), \
         patch.dict(os.environ, {"SIGNAL_ARCHIVE_API_KEY": "test-key"}):
        output = await run_post_hook(
            question="Analyze our internal db at postgres://admin:pw@host",
            body="## Analysis\n\nFound significant patterns in internal logs and system performance metrics. "
                 "The database at postgres://admin:pw@host shows high latency under peak load conditions. "
                 "Recommend adding read replicas for better performance across regions and implementing query optimization strategies. "
                 "Connection pooling and caching layers should also be evaluated for improvement.",
        )
    assert "skipped" in output.lower()


@pytest.mark.asyncio
async def test_submission_failure_returns_error_message():
    clean = SanitizationResult(
        cleaned_prompt="What is RAG?",
        was_modified=False, removed_categories=[], safe_to_submit=True, reason=""
    )
    with patch("codex_integration.hooks.post_task.sanitize_prompt", return_value=clean), \
         patch("codex_integration.hooks.post_task.ArchiveClient") as mock_cls, \
         patch.dict(os.environ, {"SIGNAL_ARCHIVE_API_KEY": "test-key"}):
        mock_client = AsyncMock()
        mock_client.submit = AsyncMock(side_effect=Exception("connection refused"))
        mock_cls.return_value = mock_client
        output = await run_post_hook(
            question="What is RAG?",
            body="## Retrieval Augmented Generation\n\nRAG combines retrieval with generation for better accuracy. "
                 "It retrieves relevant documents from https://example.com/docs and feeds them "
                 "to the LLM for grounded responses without hallucinations. Key benefit: reduces hallucinations significantly. "
                 "Implementation patterns include vector databases, semantic search, and context injection for improved model outputs.",
        )
    assert "failed" in output.lower()


@pytest.mark.asyncio
async def test_worker_type_is_codex():
    clean = SanitizationResult(
        cleaned_prompt="Compare Supabase and PlanetScale for SaaS",
        was_modified=False, removed_categories=[], safe_to_submit=True, reason=""
    )
    with patch("codex_integration.hooks.post_task.sanitize_prompt", return_value=clean), \
         patch("codex_integration.hooks.post_task.ArchiveClient") as mock_cls, \
         patch.dict(os.environ, {"SIGNAL_ARCHIVE_API_KEY": "test-key"}):
        mock_client = AsyncMock()
        mock_client.submit = AsyncMock(return_value="artifact-xyz")
        mock_cls.return_value = mock_client
        await run_post_hook(
            question="Compare Supabase and PlanetScale for SaaS",
            body="## Supabase vs PlanetScale\n\nSupabase at https://supabase.com offers Postgres with built-in authentication "
                 "and real-time capabilities. PlanetScale at https://planetscale.com uses MySQL with branching for CI/CD integration. "
                 "Choose Supabase for full-stack development needs, PlanetScale for write-heavy workloads at massive scale. "
                 "Both platforms support serverless deployments and have strong developer communities.",
            model_info="o4-mini",
        )
    payload = mock_client.submit.call_args[0][0]
    assert payload.worker_type == "codex"
    assert payload.model_info == "o4-mini"
