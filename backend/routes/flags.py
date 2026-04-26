import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from jose import JWTError
from database import get_db
from models import CommunityFlag, ResearchArtifact, Contributor
from schemas import FlagCreate
from auth import verify_jwt, hash_api_key

FLAG_ATTR = {
    "useful":         ResearchArtifact.useful_count,
    "stale":          ResearchArtifact.stale_count,
    "weakly_sourced": ResearchArtifact.weakly_sourced_count,
    "wrong":          ResearchArtifact.wrong_count,
}

router = APIRouter(tags=["flags"])


async def _resolve_contributor(
    authorization: Optional[str],
    x_api_key: Optional[str],
    db: AsyncSession,
) -> Contributor:
    """Resolve a contributor from JWT (web) or X-API-Key (agents/CLI). Raises 401 if neither."""
    if authorization and authorization.startswith("Bearer "):
        try:
            payload = verify_jwt(authorization.removeprefix("Bearer "))
            result = await db.execute(
                select(Contributor).where(Contributor.id == payload["sub"])
            )
            contributor = result.scalar_one_or_none()
            if contributor:
                return contributor
        except JWTError:
            pass

    if x_api_key:
        key_hash = hash_api_key(x_api_key)
        result = await db.execute(
            select(Contributor).where(Contributor.api_key_hash == key_hash)
        )
        contributor = result.scalar_one_or_none()
        if contributor:
            return contributor

    raise HTTPException(
        status_code=401,
        detail="Sign in to flag research. Use Bearer token (web) or X-API-Key (agents).",
    )


@router.post("", status_code=201)
async def add_flag(
    body: FlagCreate,
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    contributor = await _resolve_contributor(authorization, x_api_key, db)

    result = await db.execute(
        select(ResearchArtifact).where(ResearchArtifact.id == body.artifact_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Per-contributor deduplication
    existing = await db.execute(
        select(CommunityFlag).where(
            CommunityFlag.artifact_id == body.artifact_id,
            CommunityFlag.flag_type == body.flag_type,
            CommunityFlag.contributor_id == contributor.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You have already submitted this flag.")

    flag = CommunityFlag(
        id=uuid.uuid4(),
        artifact_id=body.artifact_id,
        flag_type=body.flag_type,
        contributor_id=contributor.id,
    )
    db.add(flag)

    col = FLAG_ATTR[body.flag_type]
    await db.execute(
        update(ResearchArtifact)
        .where(ResearchArtifact.id == body.artifact_id)
        .values({col.key: col + 1})
    )
    await db.commit()
    return {"flagged": True}
