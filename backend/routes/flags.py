import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from database import get_db
from models import CommunityFlag, ResearchArtifact
from schemas import FlagCreate

FLAG_COLUMN = {
    "useful": "useful_count",
    "stale": "stale_count",
    "weakly_sourced": "weakly_sourced_count",
    "wrong": "wrong_count",
}

router = APIRouter(tags=["flags"])

@router.post("", status_code=201)
async def add_flag(body: FlagCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ResearchArtifact).where(ResearchArtifact.id == body.artifact_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Artifact not found")
    flag = CommunityFlag(id=uuid.uuid4(), artifact_id=body.artifact_id, flag_type=body.flag_type)
    db.add(flag)
    col = FLAG_COLUMN[body.flag_type]
    await db.execute(
        text(f"UPDATE research_artifacts SET {col} = {col} + 1 WHERE id = :id"),
        {"id": str(body.artifact_id)},
    )
    await db.commit()
    return {"flagged": True}
