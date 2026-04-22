import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("OPENAI_API_KEY", "x")
os.environ.setdefault("API_KEY_SALT", "x")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("FERNET_KEY", "x")
os.environ.setdefault("RESEND_API_KEY", "")

from cryptography.fernet import Fernet
from jose import JWTError
import pytest

from auth import create_jwt, verify_jwt, encrypt_api_key, decrypt_api_key
import auth as auth_module


def test_jwt_roundtrip(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "jwt_secret", "test-secret")
    token = create_jwt(sub="user-123", handle="alice", email="alice@example.com")
    payload = verify_jwt(token)
    assert payload["sub"] == "user-123"
    assert payload["handle"] == "alice"
    assert payload["email"] == "alice@example.com"


def test_jwt_invalid_raises(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "jwt_secret", "test-secret")
    with pytest.raises(JWTError):
        verify_jwt("not.a.jwt")


def test_fernet_roundtrip(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(auth_module.settings, "fernet_key", key)
    api_key = "test-api-key-abc123"
    enc = encrypt_api_key(api_key)
    assert enc != api_key
    assert decrypt_api_key(enc) == api_key
