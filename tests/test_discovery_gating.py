import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest, uuid
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from main import app
from database import get_db
from auth import create_jwt

# --- Row factories (column order matches each endpoint's SELECT) ---

def make_rows(n):
    """weekly: (id, title, summary, run_count, reuse_count) — 5 cols"""
    return [(str(uuid.uuid4()), f"Title {i}", "Summary", i, i * 2) for i in range(n)]

def make_top_reused_rows(n):
    """top-reused: (id, title, summary, reuse_count, artifact_count, last_updated_at) — 6 cols"""
    return [
        (str(uuid.uuid4()), f"Title {i}", "Summary", i * 3, i, "2026-01-01 00:00:00")
        for i in range(n)
    ]

def make_emerging_rows(n):
    """emerging: (id, title, summary, artifact_count, reuse_count, growth_score) — 6 cols"""
    return [
        (str(uuid.uuid4()), f"Emerging {i}", "Summary", i + 2, i + 1, (i + 2) * 2 + (i + 1) * 3)
        for i in range(n)
    ]

def make_leaderboard_rows(n):
    """leaderboard: (handle, display_name, total_contributions, total_reuse_count, reputation_score) — 5 cols"""
    return [
        (f"user{i}", f"User {i}", i * 5, i * 3, float(i * 10))
        for i in range(n)
    ]

# --- /discovery/weekly ---

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

# --- /discovery/top-reused ---

@pytest.mark.asyncio
async def test_top_reused_anon_returns_3():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: make_top_reused_rows(10)))
    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/discovery/top-reused")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert len(r.json()) == 3

@pytest.mark.asyncio
async def test_top_reused_authed_returns_all():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: make_top_reused_rows(10)))
    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    token = create_jwt("u1", "alice", "a@example.com")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/discovery/top-reused", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert len(r.json()) == 10

# --- /discovery/emerging ---

@pytest.mark.asyncio
async def test_emerging_anon_returns_3():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: make_emerging_rows(10)))
    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/discovery/emerging")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert len(r.json()) == 3

@pytest.mark.asyncio
async def test_emerging_authed_returns_all():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: make_emerging_rows(10)))
    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    token = create_jwt("u1", "alice", "a@example.com")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/discovery/emerging", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert len(r.json()) == 10

# --- /discovery/leaderboard ---

@pytest.mark.asyncio
async def test_leaderboard_anon_returns_3():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: make_leaderboard_rows(10)))
    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/discovery/leaderboard")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert len(r.json()) == 3

@pytest.mark.asyncio
async def test_leaderboard_authed_returns_all():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: make_leaderboard_rows(10)))
    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    token = create_jwt("u1", "alice", "a@example.com")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/discovery/leaderboard", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert len(r.json()) == 10
