import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
from main import app
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

@pytest.mark.asyncio
async def test_flag_invalid_type_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/flags", json={
            "artifact_id": "11111111-1111-1111-1111-111111111111",
            "flag_type": "invalid_type"
        })
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_flag_valid_type_accepted():
    from database import get_db
    async def mock_get_db():
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: MagicMock()))
        mock_db.commit = AsyncMock()
        yield mock_db

    app.dependency_overrides[get_db] = mock_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/flags", json={
                "artifact_id": "11111111-1111-1111-1111-111111111111",
                "flag_type": "useful"
            })
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 201
