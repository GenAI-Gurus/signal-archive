import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sanitizer'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'worker_sdk'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, AsyncMock
from sanitizer import SanitizationResult
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

    assert "artifact-id-123" in output
