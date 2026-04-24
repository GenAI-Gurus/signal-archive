import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
import uuid
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from main import app
from database import get_db


def _make_cq(title="Test question"):
    m = MagicMock()
    m.id = uuid.uuid4()
    m.title = title
    m.synthesized_summary = "A summary."
    m.artifact_count = 3
    m.reuse_count = 7
    m.created_at = datetime(2026, 4, 1)
    m.last_updated_at = datetime(2026, 4, 2)
    return m


@pytest.mark.asyncio
async def test_canonical_list_returns_items():
    fake_rows = [_make_cq(f"Question {i}") for i in range(5)]
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: fake_rows)))

    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/canonical")
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 5
    assert body[0]["title"] == "Question 0"


@pytest.mark.asyncio
async def test_canonical_list_respects_limit():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/canonical?limit=101")
    assert r.status_code == 422  # limit exceeds max


@pytest.mark.asyncio
async def test_canonical_list_rejects_invalid_sort():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/canonical?sort=invalid")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_canonical_list_sort_popular():
    fake_rows = [_make_cq("Popular question")]
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: fake_rows)))

    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/canonical?sort=popular")
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert r.json()[0]["title"] == "Popular question"

    # Verify the query was ordered by reuse_count (not last_updated_at)
    stmt = mock_db.execute.call_args[0][0]
    order_keys = [str(c) for c in stmt._order_by_clauses]
    assert any("reuse_count" in k for k in order_keys)
    assert not any("last_updated_at" in k for k in order_keys)
