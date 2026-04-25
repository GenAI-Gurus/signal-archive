import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_synthesize_summary_calls_openai_with_question_and_answers():
    """synthesize_summary passes question and up to 10 short_answers to OpenAI."""
    from summarizer import synthesize_summary

    fake_choice = MagicMock()
    fake_choice.message.content = "  Quantum computing uses qubits. It enables exponential speedups.  "
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]

    mock_create = AsyncMock(return_value=fake_response)

    with patch("summarizer._client") as mock_client:
        mock_client.chat.completions.create = mock_create
        result = await synthesize_summary(
            question="How does quantum computing work?",
            short_answers=["Uses qubits", "Superposition enables speedup"],
        )

    assert result == "Quantum computing uses qubits. It enables exponential speedups."
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["max_tokens"] == 200
    messages = call_kwargs["messages"]
    user_msg = next(m for m in messages if m["role"] == "user")
    assert "quantum computing" in user_msg["content"].lower()
    assert "Uses qubits" in user_msg["content"]


@pytest.mark.asyncio
async def test_synthesize_summary_truncates_to_ten_answers():
    """Only the first 10 short_answers are included in the prompt."""
    from summarizer import synthesize_summary

    fake_choice = MagicMock()
    fake_choice.message.content = "Summary."
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]

    mock_create = AsyncMock(return_value=fake_response)

    with patch("summarizer._client") as mock_client:
        mock_client.chat.completions.create = mock_create
        await synthesize_summary(
            question="Question?",
            short_answers=[f"Answer {i}" for i in range(15)],
        )

    user_msg_content = mock_create.call_args.kwargs["messages"][-1]["content"]
    assert "Answer 10" not in user_msg_content
    assert "Answer 9" in user_msg_content


@pytest.mark.asyncio
async def test_synthesize_summary_returns_empty_string_for_no_answers():
    """Returns empty string without calling OpenAI when short_answers is empty."""
    from summarizer import synthesize_summary

    with patch("summarizer._client") as mock_client:
        result = await synthesize_summary(question="Question?", short_answers=[])

    mock_client.chat.completions.create.assert_not_called()
    assert result == ""


@pytest.mark.asyncio
async def test_synthesize_summary_sorts_by_weight_descending():
    """When weights are provided, higher-weight answers appear first and carry quality badges."""
    from summarizer import synthesize_summary

    fake_choice = MagicMock()
    fake_choice.message.content = "Summary."
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]
    mock_create = AsyncMock(return_value=fake_response)

    with patch("summarizer._client") as mock_client:
        mock_client.chat.completions.create = mock_create
        await synthesize_summary(
            question="Which vector DB is best?",
            short_answers=["Low quality answer.", "High quality answer."],
            weights=[20.0, 90.0],
        )

    user_msg = mock_create.call_args.kwargs["messages"][-1]["content"]
    # High-quality answer (weight 90) must appear before low-quality (weight 20)
    assert user_msg.index("High quality") < user_msg.index("Low quality")
    # Quality scores annotated in the prompt
    assert "90" in user_msg
    assert "20" in user_msg


@pytest.mark.asyncio
async def test_synthesize_summary_without_weights_unchanged():
    """Calling without weights preserves existing behavior (no quality badges)."""
    from summarizer import synthesize_summary

    fake_choice = MagicMock()
    fake_choice.message.content = "Summary."
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]
    mock_create = AsyncMock(return_value=fake_response)

    with patch("summarizer._client") as mock_client:
        mock_client.chat.completions.create = mock_create
        result = await synthesize_summary(
            question="Question?",
            short_answers=["Answer A.", "Answer B."],
        )

    assert result == "Summary."
    user_msg = mock_create.call_args.kwargs["messages"][-1]["content"]
    # No quality scores when weights not provided
    assert "score:" not in user_msg
