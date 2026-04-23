from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db
from auth import get_optional_jwt
from typing import Optional

router = APIRouter(tags=["discovery"])

ANON_LIMIT = 3

@router.get("/weekly")
async def weekly_research(
    db: AsyncSession = Depends(get_db),
    jwt_payload: Optional[dict] = Depends(get_optional_jwt),
):
    limit = 20 if jwt_payload else ANON_LIMIT
    result = await db.execute(text("""
        SELECT cq.id, cq.title, cq.synthesized_summary, COUNT(ra.id) AS run_count, cq.reuse_count
        FROM canonical_questions cq
        JOIN research_artifacts ra ON ra.canonical_question_id = cq.id
        WHERE ra.created_at >= NOW() - INTERVAL '7 days'
        GROUP BY cq.id
        ORDER BY run_count DESC
        LIMIT :limit
    """), {"limit": limit})
    rows = result.fetchall()
    return [
        {"canonical_question_id": str(r[0]), "title": r[1], "summary": r[2], "run_count": r[3], "reuse_count": r[4]}
        for r in rows
    ]

@router.get("/top-reused")
async def top_reused(
    db: AsyncSession = Depends(get_db),
    jwt_payload: Optional[dict] = Depends(get_optional_jwt),
):
    limit = 20 if jwt_payload else ANON_LIMIT
    result = await db.execute(text("""
        SELECT id, title, synthesized_summary, reuse_count, artifact_count, last_updated_at
        FROM canonical_questions
        ORDER BY reuse_count DESC
        LIMIT :limit
    """), {"limit": limit})
    rows = result.fetchall()
    return [
        {"canonical_question_id": str(r[0]), "title": r[1], "summary": r[2],
         "reuse_count": r[3], "artifact_count": r[4], "last_updated_at": str(r[5])}
        for r in rows
    ]

@router.get("/emerging")
async def emerging_topics(
    db: AsyncSession = Depends(get_db),
    jwt_payload: Optional[dict] = Depends(get_optional_jwt),
):
    """Canonical questions created in the last 14 days with growth signals."""
    limit = 20 if jwt_payload else ANON_LIMIT
    result = await db.execute(text("""
        SELECT
            cq.id,
            cq.title,
            cq.synthesized_summary,
            cq.artifact_count,
            cq.reuse_count,
            (cq.artifact_count * 2 + cq.reuse_count * 3) AS growth_score
        FROM canonical_questions cq
        WHERE cq.created_at >= NOW() - INTERVAL '14 days'
          AND (cq.artifact_count >= 2 OR cq.reuse_count >= 1)
        ORDER BY growth_score DESC, cq.created_at DESC
        LIMIT :limit
    """), {"limit": limit})
    rows = result.fetchall()
    return [
        {
            "canonical_question_id": str(r[0]),
            "title": r[1],
            "summary": r[2],
            "artifact_count": r[3],
            "reuse_count": r[4],
            "growth_score": r[5],
        }
        for r in rows
    ]

@router.get("/leaderboard")
async def leaderboard(
    db: AsyncSession = Depends(get_db),
    jwt_payload: Optional[dict] = Depends(get_optional_jwt),
):
    limit = 20 if jwt_payload else ANON_LIMIT
    result = await db.execute(text("""
        SELECT handle, display_name, total_contributions, total_reuse_count, reputation_score
        FROM contributors
        ORDER BY total_reuse_count DESC, total_contributions DESC
        LIMIT :limit
    """), {"limit": limit})
    rows = result.fetchall()
    return [
        {"handle": r[0], "display_name": r[1], "total_contributions": r[2],
         "total_reuse_count": r[3], "reputation_score": round(r[4], 2)}
        for r in rows
    ]
