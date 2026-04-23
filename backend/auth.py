import hashlib
import resend
from datetime import datetime, timezone, timedelta
from typing import Optional
from cryptography.fernet import Fernet
from jose import jwt, JWTError
from fastapi import HTTPException, Header
from config import settings

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 30

if settings.resend_api_key:
    resend.api_key = settings.resend_api_key


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256((api_key + settings.api_key_salt).encode()).hexdigest()


def encrypt_api_key(api_key: str) -> str:
    f = Fernet(settings.fernet_key.encode())
    return f.encrypt(api_key.encode()).decode()


def decrypt_api_key(enc: str) -> str:
    f = Fernet(settings.fernet_key.encode())
    return f.decrypt(enc.encode()).decode()


def create_jwt(sub: str, handle: str, email: str) -> str:
    payload = {
        "sub": sub,
        "handle": handle,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def verify_jwt(token: str) -> dict:
    """Raises JWTError if invalid or expired."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])


def get_optional_jwt(authorization: Optional[str] = Header(default=None)) -> Optional[dict]:
    """Returns decoded payload if valid Bearer token present, else None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return verify_jwt(authorization.removeprefix("Bearer "))
    except JWTError:
        return None


def require_jwt(authorization: Optional[str] = Header(default=None)) -> dict:
    """Raises HTTP 401 if no valid Bearer token."""
    payload = get_optional_jwt(authorization)
    if payload is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return payload


def send_magic_link(email: str, magic_url: str) -> None:
    """Send magic link email via Resend. Prints to stdout in dev (empty RESEND_API_KEY)."""
    if not magic_url.startswith("https://"):
        raise ValueError(f"magic_url must use https: {magic_url!r}")
    if not settings.resend_api_key:
        print(f"[DEV] Magic link for {email}: {magic_url}")
        return
    try:
        resend.Emails.send({
            "from": "Signal Archive <noreply@auth.genai-gurus.com>",
            "to": [email],
            "subject": "Your Signal Archive login link",
            "html": (
                "<p>Click below to sign in to Signal Archive. Expires in 15 minutes.</p>"
                f'<p><a href="{magic_url}">Sign in to Signal Archive</a></p>'
                "<p style='color:#666;font-size:12px'>If you didn't request this, ignore this email.</p>"
            ),
        })
    except Exception as exc:
        print(f"[ERROR] Resend failed for {email}: {exc}")
        raise HTTPException(status_code=502, detail="Email delivery failed. Please try again later.")
