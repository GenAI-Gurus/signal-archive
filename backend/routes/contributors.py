import hashlib
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Contributor
from schemas import ContributorCreate, ContributorCreated, ContributorResponse
from config import settings

router = APIRouter(tags=["contributors"])

def _hash_key(api_key: str) -> str:
    return hashlib.sha256((api_key + settings.api_key_salt).encode()).hexdigest()

@router.post("", status_code=201, response_model=ContributorCreated)
async def create_contributor(body: ContributorCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Contributor).where(Contributor.handle == body.handle))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Handle already taken")
    api_key = secrets.token_urlsafe(32)
    contributor = Contributor(
        handle=body.handle,
        display_name=body.display_name,
        api_key_hash=_hash_key(api_key),
    )
    db.add(contributor)
    await db.commit()
    await db.refresh(contributor)
    return ContributorCreated(handle=contributor.handle, api_key=api_key)

@router.get("/{handle}", response_model=ContributorResponse)
async def get_contributor(handle: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contributor).where(Contributor.handle == handle))
    contributor = result.scalar_one_or_none()
    if not contributor:
        raise HTTPException(status_code=404, detail="Contributor not found")
    return contributor
