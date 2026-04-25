import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("OPENAI_API_KEY", "x")
os.environ.setdefault("API_KEY_SALT", "x")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("FERNET_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
os.environ.setdefault("RESEND_API_KEY", "")


def _mock_llm_response(word: str):
    msg = MagicMock()
    msg.content = word
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.mark.asyncio
async def test_score_high_quality():
    """20 sources, 2000-word body, faithful short answer → score near 100."""
    from quality import compute_quality_score

    source_domains = [f"domain{i}.com" for i in range(20)]
    full_body = " ".join(["word"] * 2000)
    short_answer = "A faithful summary."

    with patch("quality._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_llm_response("YES")
        )
        score = await compute_quality_score(source_domains, full_body, short_answer)

    assert score == 100.0


@pytest.mark.asyncio
async def test_score_partial_faithfulness():
    """20 sources, 2000-word body, PARTIAL faithfulness → 85 pts (40+30+15)."""
    from quality import compute_quality_score

    source_domains = [f"domain{i}.com" for i in range(20)]
    full_body = " ".join(["word"] * 2000)
    short_answer = "Somewhat summarises it."

    with patch("quality._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_llm_response("PARTIAL")
        )
        score = await compute_quality_score(source_domains, full_body, short_answer)

    assert score == 85.0  # 40 + 30 + 15


@pytest.mark.asyncio
async def test_score_low_quality():
    """2 sources, 300-word body, unfaithful short answer → low score."""
    from quality import compute_quality_score

    source_domains = ["a.com", "b.com"]
    full_body = " ".join(["word"] * 300)
    short_answer = "Wrong claim."

    with patch("quality._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_llm_response("NO")
        )
        score = await compute_quality_score(source_domains, full_body, short_answer)

    # source: min(40, 2/20*40) = 4; word: min(30, 300/2000*30) = 4.5; faith: 0
    assert score == pytest.approx(8.5, abs=0.1)


@pytest.mark.asyncio
async def test_score_caps_at_100():
    """50 sources and 5000 words should not exceed 100."""
    from quality import compute_quality_score

    source_domains = [f"domain{i}.com" for i in range(50)]
    full_body = " ".join(["word"] * 5000)
    short_answer = "Great summary."

    with patch("quality._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            return_value=_mock_llm_response("YES")
        )
        score = await compute_quality_score(source_domains, full_body, short_answer)

    assert score == 100.0


@pytest.mark.asyncio
async def test_llm_error_falls_back_to_zero_faithfulness():
    """If LLM call raises, faithfulness defaults to 0 and function still returns a score."""
    from quality import compute_quality_score

    source_domains = [f"domain{i}.com" for i in range(10)]
    full_body = " ".join(["word"] * 1000)
    short_answer = "Some answer."

    with patch("quality._client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("timeout"))
        score = await compute_quality_score(source_domains, full_body, short_answer)

    # source: min(40, 10/20*40) = 20; word: min(30, 1000/2000*30) = 15; faith: 0
    assert score == pytest.approx(35.0, abs=0.1)
