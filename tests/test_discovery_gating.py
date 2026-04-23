import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest, uuid
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from main import app
from database import get_db
from auth import create_jwt

def make_rows(n):
    return [(str(uuid.uuid4()), f"Title {i}", "Summary", i, i * 2) for i in range(n)]

@pytest.mark.asyncio
async def test_weekly_anon_returns_3():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: make_rows(10)))
    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/discovery/weekly")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert len(r.json()) == 3

@pytest.mark.asyncio
async def test_weekly_authed_returns_all():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: make_rows(10)))
    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    token = create_jwt("u1", "alice", "a@example.com")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/discovery/weekly", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert len(r.json()) == 10
