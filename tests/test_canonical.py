import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_returns_existing_canonical_when_similarity_high():
    """When a match is found, canonical_id is returned and synthesized_summary is updated."""
    from canonical import find_or_create_canonical

    existing_id = "11111111-1111-1111-1111-111111111111"

    similarity_result = MagicMock()
    similarity_result.fetchall = lambda: [(existing_id, "What is the best Python ORM?", 0.93)]

    # Now returns (short_answer, quality_score) tuples
    short_answer_result = MagicMock()
    short_answer_result.fetchall = lambda: [("SQLAlchemy is popular.", 75.0), ("Django ORM is simpler.", None)]

    update_result = MagicMock()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[similarity_result, short_answer_result, update_result])

    embedding = [0.1] * 1536

    synthesize_mock = AsyncMock(return_value="ORM synthesis.")
    with patch("canonical.synthesize_summary", new=synthesize_mock):
        result, created = await find_or_create_canonical(
            db=mock_db,
            question="Best Python ORM options?",
            embedding=embedding,
            summary="Peewee is lightweight.",
        )

    assert result == existing_id
    assert created is False
    assert mock_db.execute.call_count == 3
    update_call_kwargs = mock_db.execute.call_args_list[2][0][1]
    assert update_call_kwargs["summary"] == "ORM synthesis."
    # Weights were passed: new artifact gets 50 (neutral), existing get their scores or 50 for None
    call_kwargs = synthesize_mock.call_args.kwargs
    assert "weights" in call_kwargs
    weights = call_kwargs["weights"]
    assert weights[0] == 50.0   # new artifact's weight (no score yet)
    assert weights[1] == 75.0   # first existing artifact
    assert weights[2] == 50.0   # second existing artifact had None → default 50.0


@pytest.mark.asyncio
async def test_existing_canonical_falls_back_on_summarizer_error():
    """If synthesize_summary raises, the artifact_count UPDATE still happens."""
    from canonical import find_or_create_canonical

    existing_id = "22222222-2222-2222-2222-222222222222"

    similarity_result = MagicMock()
    similarity_result.fetchall = lambda: [(existing_id, "Some question", 0.95)]

    short_answer_result = MagicMock()
    short_answer_result.fetchall = lambda: [("Answer A.", 80.0)]

    update_result = MagicMock()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[similarity_result, short_answer_result, update_result])

    embedding = [0.1] * 1536

    with patch("canonical.synthesize_summary", new=AsyncMock(side_effect=Exception("OpenAI down"))):
        result, created = await find_or_create_canonical(
            db=mock_db,
            question="Some question?",
            embedding=embedding,
            summary="New short answer.",
        )

    assert result == existing_id
    assert created is False
    # Should still have issued 3 execute calls (search, fetch short_answers, fallback UPDATE)
    assert mock_db.execute.call_count == 3


@pytest.mark.asyncio
async def test_creates_new_canonical_when_no_match():
    """When no match is found, a new canonical is created."""
    from canonical import find_or_create_canonical

    no_match_result = MagicMock()
    no_match_result.fetchall = lambda: []

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=no_match_result)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    embedding = [0.1] * 1536
    result, created = await find_or_create_canonical(
        db=mock_db,
        question="How does quantum computing work?",
        embedding=embedding,
        summary="Overview of quantum computing",
    )

    assert created is True
    assert result is not None


@pytest.mark.asyncio
async def test_existing_canonical_passes_quality_weights_to_summarizer():
    """quality_score values from DB are converted to weights; None → 50.0."""
    from canonical import find_or_create_canonical

    existing_id = "33333333-3333-3333-3333-333333333333"

    similarity_result = MagicMock()
    similarity_result.fetchall = lambda: [(existing_id, "Some question", 0.91)]

    short_answer_result = MagicMock()
    short_answer_result.fetchall = lambda: [("High quality answer.", 95.0), ("Unscored answer.", None)]

    update_result = MagicMock()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[similarity_result, short_answer_result, update_result])

    synthesize_mock = AsyncMock(return_value="Synthesis.")
    with patch("canonical.synthesize_summary", new=synthesize_mock):
        await find_or_create_canonical(
            db=mock_db,
            question="Some question?",
            embedding=[0.1] * 1536,
            summary="New short answer.",
        )

    call_kwargs = synthesize_mock.call_args.kwargs
    weights = call_kwargs["weights"]
    # 3 answers: new (50.0), high-quality (95.0), unscored (50.0)
    assert len(weights) == 3
    assert weights[0] == 50.0
    assert weights[1] == 95.0
    assert weights[2] == 50.0
