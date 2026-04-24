import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database import get_db
from models import CommunityFlag, ResearchArtifact
from schemas import FlagCreate

FLAG_ATTR = {
    "useful": ResearchArtifact.useful_count,
    "stale": ResearchArtifact.stale_count,
    "weakly_sourced": ResearchArtifact.weakly_sourced_count,
    "wrong": ResearchArtifact.wrong_count,
}

router = APIRouter(tags=["flags"])

@router.post("", status_code=201)
async def add_flag(body: FlagCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ResearchArtifact).where(ResearchArtifact.id == body.artifact_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Artifact not found")
    flag = CommunityFlag(id=uuid.uuid4(), artifact_id=body.artifact_id, flag_type=body.flag_type)
    db.add(flag)
    col = FLAG_ATTR[body.flag_type]
    await db.execute(
        update(ResearchArtifact)
        .where(ResearchArtifact.id == body.artifact_id)
        .values({col.key: col + 1})
    )
    await db.commit()
    return {"flagged": True}
