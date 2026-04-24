import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from database import get_db
from models import CanonicalQuestion, ResearchArtifact, ReuseEvent
from schemas import CanonicalQuestionResponse, ArtifactResponse, SearchResult

router = APIRouter(tags=["canonical"])

@router.get("", response_model=list[CanonicalQuestionResponse])
async def list_canonical(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: Literal["recent", "popular", "active"] = Query(default="recent"),
    db: AsyncSession = Depends(get_db),
):
    order_col = {
        "recent": CanonicalQuestion.last_updated_at.desc(),
        "popular": CanonicalQuestion.reuse_count.desc(),
        "active": CanonicalQuestion.artifact_count.desc(),
    }[sort]
    result = await db.execute(
        select(CanonicalQuestion).order_by(order_col).offset(offset).limit(limit)
    )
    return result.scalars().all()

@router.get("/{canonical_id}", response_model=CanonicalQuestionResponse)
async def get_canonical(canonical_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CanonicalQuestion).where(CanonicalQuestion.id == canonical_id))
    cq = result.scalar_one_or_none()
    if not cq:
        raise HTTPException(status_code=404, detail="Canonical question not found")
    return cq

@router.get("/{canonical_id}/artifacts", response_model=list[ArtifactResponse])
async def get_canonical_artifacts(
    canonical_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ResearchArtifact)
        .where(ResearchArtifact.canonical_question_id == canonical_id)
        .order_by(ResearchArtifact.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()

@router.get("/{canonical_id}/related", response_model=list[SearchResult])
async def get_related(canonical_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CanonicalQuestion).where(CanonicalQuestion.id == canonical_id))
    cq = result.scalar_one_or_none()
    if not cq or cq.embedding is None:
        return []
    if not all(isinstance(v, (int, float)) for v in cq.embedding):
        return []
    vector_literal = f"[{','.join(str(float(v)) for v in cq.embedding)}]"
    rows = await db.execute(text(f"""
        SELECT id, title, synthesized_summary,
               1 - (embedding <=> '{vector_literal}'::vector) AS similarity,
               artifact_count, reuse_count, last_updated_at
        FROM canonical_questions
        WHERE id != :id AND embedding IS NOT NULL
        ORDER BY embedding <=> '{vector_literal}'::vector
        LIMIT 5
    """), {"id": canonical_id})
    return [
        SearchResult(
            canonical_question_id=r[0], title=r[1], synthesized_summary=r[2],
            similarity=round(float(r[3]), 4), artifact_count=r[4],
            reuse_count=r[5], last_updated_at=r[6],
        )
        for r in rows.fetchall()
    ]

@router.post("/{canonical_id}/reuse", status_code=201)
async def record_reuse(canonical_id: str, reused_by: str = None, db: AsyncSession = Depends(get_db)):
    event = ReuseEvent(id=uuid.uuid4(), canonical_question_id=canonical_id, reused_by=reused_by)
    db.add(event)
    await db.execute(
        text("UPDATE canonical_questions SET reuse_count = reuse_count + 1 WHERE id = :id"),
        {"id": canonical_id},
    )
    await db.commit()
    return {"recorded": True}
