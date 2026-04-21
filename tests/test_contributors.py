import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from main import app
from database import get_db

@pytest.mark.asyncio
async def test_create_contributor_returns_api_key():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/contributors", json={"handle": "alice", "display_name": "Alice"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert "api_key" in data
    assert data["handle"] == "alice"

@pytest.mark.asyncio
async def test_get_contributor_not_found():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/contributors/nonexistent")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
