import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest, uuid
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock
from main import app
from database import get_db


@pytest.mark.asyncio
async def test_request_login_sends_link():
    mock_db = AsyncMock()
    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    try:
        with patch("routes.auth.send_magic_link") as mock_send:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/auth/request-login", json={"email": "user@example.com"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json()["message"] == "Magic link sent"
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_verify_new_user_requires_handle():
    import secrets, hashlib
    from datetime import datetime, timezone, timedelta
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    fake_token = MagicMock()
    fake_token.email = "new@example.com"
    fake_token.used = False
    fake_token.expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    fake_token.cli_session_id = None

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=lambda: fake_token),   # find token
        MagicMock(scalar_one_or_none=lambda: None),          # find contributor by email -> not found
    ])
    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/auth/verify", json={"token": raw_token})  # no handle
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 422  # handle required for new users


@pytest.mark.asyncio
async def test_verify_new_user_with_handle():
    import secrets, hashlib
    from datetime import datetime, timezone, timedelta
    raw_token = secrets.token_urlsafe(32)
    fake_token = MagicMock()
    fake_token.email = "new@example.com"
    fake_token.used = False
    fake_token.expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    fake_token.cli_session_id = None

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=lambda: fake_token),   # find token
        MagicMock(scalar_one_or_none=lambda: None),          # find contributor by email
        MagicMock(scalar_one_or_none=lambda: None),          # check handle uniqueness
    ])
    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    try:
        with patch("routes.auth.encrypt_api_key", return_value="enc"), \
             patch("routes.auth.hash_api_key", return_value="hashed"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/auth/verify", json={"token": raw_token, "handle": "newuser"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    data = r.json()
    assert data["is_new"] is True
    assert data["handle"] == "newuser"
    assert "jwt" in data
    assert "api_key" in data


@pytest.mark.asyncio
async def test_cli_session_create():
    mock_db = AsyncMock()
    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/auth/cli-session")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert "session_id" in r.json()
    assert "login_url" in r.json()


@pytest.mark.asyncio
async def test_cli_session_poll_not_ready():
    from datetime import datetime, timezone, timedelta
    session_id = uuid.uuid4()
    fake_session = MagicMock()
    fake_session.api_key = None
    fake_session.claimed = False
    fake_session.expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: fake_session))
    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"/auth/cli-session/{session_id}/poll")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json()["ready"] is False


@pytest.mark.asyncio
async def test_token_returns_jwt_for_valid_api_key():
    from auth import create_jwt, hash_api_key
    import uuid
    from unittest.mock import AsyncMock, MagicMock
    from database import get_db
    from main import app

    raw_key = "test-api-key-abc123"

    fake_contributor = MagicMock()
    fake_contributor.id = uuid.uuid4()
    fake_contributor.handle = "tester"
    fake_contributor.email = "tester@example.com"

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=lambda: fake_contributor
    ))

    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/auth/token", json={"api_key": raw_key})
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert "jwt" in body
    assert body["handle"] == "tester"
    assert body["email"] == "tester@example.com"


@pytest.mark.asyncio
async def test_token_returns_401_for_invalid_key():
    from database import get_db
    from main import app

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=lambda: None
    ))

    async def override(): yield mock_db
    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/auth/token", json={"api_key": "wrong-key"})
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 401
