import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_returns_existing_canonical_when_similarity_high():
    from canonical import find_or_create_canonical
    mock_db = AsyncMock()
    existing_id = "11111111-1111-1111-1111-111111111111"
    mock_db.execute = AsyncMock(return_value=MagicMock(
        fetchall=lambda: [(existing_id, "What is the best Python ORM?", 0.93)]
    ))
    embedding = [0.1] * 1536
    result, created = await find_or_create_canonical(
        db=mock_db,
        question="Best Python ORM options?",
        embedding=embedding,
        summary="A review of Python ORMs"
    )
    assert result == existing_id
    assert created is False

@pytest.mark.asyncio
async def test_creates_new_canonical_when_no_match():
    from canonical import find_or_create_canonical
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    embedding = [0.1] * 1536
    result, created = await find_or_create_canonical(
        db=mock_db,
        question="How does quantum computing work?",
        embedding=embedding,
        summary="Overview of quantum computing"
    )
    assert created is True
