import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_returns_existing_canonical_when_similarity_high():
    """When a match is found, canonical_id is returned and synthesized_summary is updated."""
    from canonical import find_or_create_canonical

    existing_id = "11111111-1111-1111-1111-111111111111"

    # 1st call: similarity search → match
    similarity_result = MagicMock()
    similarity_result.fetchall = lambda: [(existing_id, "What is the best Python ORM?", 0.93)]

    # 2nd call: fetch existing short_answers
    short_answer_result = MagicMock()
    short_answer_result.fetchall = lambda: [("SQLAlchemy is popular.",), ("Django ORM is simpler.",)]

    # 3rd call: UPDATE with new summary
    update_result = MagicMock()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[similarity_result, short_answer_result, update_result])

    embedding = [0.1] * 1536

    with patch("canonical.synthesize_summary", new=AsyncMock(return_value="ORM synthesis.")):
        result, created = await find_or_create_canonical(
            db=mock_db,
            question="Best Python ORM options?",
            embedding=embedding,
            summary="Peewee is lightweight.",
        )

    assert result == existing_id
    assert created is False
    assert mock_db.execute.call_count == 3


@pytest.mark.asyncio
async def test_existing_canonical_falls_back_on_summarizer_error():
    """If synthesize_summary raises, the artifact_count UPDATE still happens."""
    from canonical import find_or_create_canonical

    existing_id = "22222222-2222-2222-2222-222222222222"

    similarity_result = MagicMock()
    similarity_result.fetchall = lambda: [(existing_id, "Some question", 0.95)]

    short_answer_result = MagicMock()
    short_answer_result.fetchall = lambda: [("Answer A.",)]

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
