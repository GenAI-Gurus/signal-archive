import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from uuid import UUID as PyUUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Contributor, MagicLinkToken, CliSession
from schemas import (
    MagicLinkRequest, MagicLinkVerify, AuthResponse,
    CliSessionResponse, CliSessionPoll,
    TokenRequest, TokenResponse,
)
from auth import hash_api_key, encrypt_api_key, decrypt_api_key, create_jwt, send_magic_link

FRONTEND_BASE = "https://genai-gurus.com/signal-archive"
MAGIC_LINK_EXPIRY_MINUTES = 15
CLI_SESSION_EXPIRY_MINUTES = 10

router = APIRouter(tags=["auth"])


@router.post("/request-login")
async def request_login(body: MagicLinkRequest, db: AsyncSession = Depends(get_db)):
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    cli_session_id = None
    if body.cli_session_id:
        try:
            cli_session_id = PyUUID(body.cli_session_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="cli_session_id is not a valid UUID")
    db.add(MagicLinkToken(
        email=body.email.lower().strip(),
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=MAGIC_LINK_EXPIRY_MINUTES),
        cli_session_id=cli_session_id,
    ))
    await db.commit()
    magic_url = f"{FRONTEND_BASE}/auth/callback?token={raw_token}"
    if cli_session_id:
        magic_url += f"&cli_session={cli_session_id}"
    send_magic_link(body.email.lower().strip(), magic_url)
    return {"message": "Magic link sent"}


@router.post("/verify", response_model=AuthResponse)
async def verify_magic_link(body: MagicLinkVerify, db: AsyncSession = Depends(get_db)):
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    result = await db.execute(
        select(MagicLinkToken).where(MagicLinkToken.token_hash == token_hash)
    )
    token_row = result.scalar_one_or_none()
    if not token_row:
        raise HTTPException(status_code=404, detail="Invalid token")
    if token_row.used:
        raise HTTPException(status_code=410, detail="Token already used")
    if token_row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Token expired")

    email = token_row.email
    result2 = await db.execute(select(Contributor).where(Contributor.email == email))
    contributor = result2.scalar_one_or_none()

    is_new = contributor is None
    if is_new:
        if not body.handle:
            raise HTTPException(status_code=422, detail="handle is required for new accounts")
        existing = await db.execute(
            select(Contributor).where(Contributor.handle == body.handle)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Handle already taken")
        api_key = secrets.token_urlsafe(32)
        contributor = Contributor(
            handle=body.handle,
            display_name=body.display_name,
            email=email,
            email_verified=True,
            api_key_hash=hash_api_key(api_key),
            api_key_enc=encrypt_api_key(api_key),
        )
        db.add(contributor)
    else:
        contributor.email_verified = True
        api_key = decrypt_api_key(contributor.api_key_enc)

    if token_row.cli_session_id:
        cli_result = await db.execute(
            select(CliSession).where(CliSession.id == token_row.cli_session_id)
        )
        cli_session = cli_result.scalar_one_or_none()
        if cli_session and not cli_session.claimed:
            cli_session.api_key = api_key
            cli_session.claimed = True

    token_row.used = True  # mark used only after all validation passes
    await db.commit()
    if is_new:
        await db.refresh(contributor)

    return AuthResponse(
        jwt=create_jwt(str(contributor.id), contributor.handle, contributor.email),
        handle=contributor.handle,
        email=contributor.email,
        is_new=is_new,
        api_key=api_key,
    )


@router.post("/cli-session", response_model=CliSessionResponse)
async def create_cli_session(db: AsyncSession = Depends(get_db)):
    session = CliSession(
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=CLI_SESSION_EXPIRY_MINUTES),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return CliSessionResponse(
        session_id=str(session.id),
        login_url=f"{FRONTEND_BASE}/login?cli_session={session.id}",
    )


@router.get("/cli-session/{session_id}/poll", response_model=CliSessionPoll)
async def poll_cli_session(session_id: PyUUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CliSession).where(CliSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Session expired")
    if session.claimed and session.api_key:
        return CliSessionPoll(ready=True, api_key=session.api_key)
    return CliSessionPoll(ready=False)


@router.post("/token", response_model=TokenResponse)
async def exchange_api_key(body: TokenRequest, db: AsyncSession = Depends(get_db)):
    """Exchange an api_key for a JWT. Use the returned JWT as Bearer token for all subsequent requests."""
    key_hash = hash_api_key(body.api_key)
    result = await db.execute(select(Contributor).where(Contributor.api_key_hash == key_hash))
    contributor = result.scalar_one_or_none()
    if not contributor:
        raise HTTPException(status_code=401, detail="Invalid api_key")
    return TokenResponse(
        jwt=create_jwt(str(contributor.id), contributor.handle, contributor.email or ""),
        handle=contributor.handle,
        email=contributor.email or "",
    )
