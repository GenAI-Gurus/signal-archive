import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from main import app
from database import get_db

@pytest.mark.asyncio
async def test_search_requires_query():
    from auth import create_jwt
    token = create_jwt("u1", "alice", "a@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/search", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_search_returns_results():
    import uuid
    from datetime import datetime
    from auth import create_jwt
    fake_embedding = [0.1] * 1536
    fake_cq_id = uuid.uuid4()
    fake_rows = [(str(fake_cq_id), "What are vector databases?", "Overview of vector DBs", 0.95, 3, 12, datetime(2026, 4, 1))]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: fake_rows))

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    token = create_jwt("u1", "alice", "a@example.com")
    try:
        with patch("routes.search.get_embedding", new_callable=AsyncMock, return_value=fake_embedding):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/search?q=best+vector+databases", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["similarity"] == 0.95

@pytest.mark.asyncio
async def test_search_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/search?q=hello")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_search_accepts_valid_jwt():
    import uuid
    from datetime import datetime
    from auth import create_jwt
    fake_embedding = [0.1] * 1536
    fake_rows = [(str(uuid.uuid4()), "Title", "Summary", 0.9, 2, 5, datetime(2026, 4, 1))]
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: fake_rows))
    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    token = create_jwt("u1", "alice", "a@example.com")
    try:
        with patch("routes.search.get_embedding", new_callable=AsyncMock, return_value=fake_embedding):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.get("/search?q=hello", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
