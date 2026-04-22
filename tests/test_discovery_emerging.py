import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from main import app
from database import get_db

@pytest.mark.asyncio
async def test_emerging_endpoint_returns_list():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: [
        ("cq-id-1", "What is Fly.io?", "Overview of Fly.io", 3, 2, 12)
    ]))

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/discovery/emerging")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["title"] == "What is Fly.io?"
    assert "growth_score" in data[0]

@pytest.mark.asyncio
async def test_emerging_endpoint_returns_empty_list_when_no_data():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/discovery/emerging")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json() == []
