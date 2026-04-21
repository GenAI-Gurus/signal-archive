from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db

router = APIRouter(tags=["discovery"])

@router.get("/weekly")
async def weekly_research(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("""
        SELECT cq.id, cq.title, cq.synthesized_summary, COUNT(ra.id) AS run_count, cq.reuse_count
        FROM canonical_questions cq
        JOIN research_artifacts ra ON ra.canonical_question_id = cq.id
        WHERE ra.created_at >= NOW() - INTERVAL '7 days'
        GROUP BY cq.id
        ORDER BY run_count DESC
        LIMIT 20
    """))
    rows = result.fetchall()
    return [
        {"canonical_question_id": str(r[0]), "title": r[1], "summary": r[2], "run_count": r[3], "reuse_count": r[4]}
        for r in rows
    ]

@router.get("/top-reused")
async def top_reused(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("""
        SELECT id, title, synthesized_summary, reuse_count, artifact_count, last_updated_at
        FROM canonical_questions
        ORDER BY reuse_count DESC
        LIMIT 20
    """))
    rows = result.fetchall()
    return [
        {"canonical_question_id": str(r[0]), "title": r[1], "summary": r[2],
         "reuse_count": r[3], "artifact_count": r[4], "last_updated_at": str(r[5])}
        for r in rows
    ]

@router.get("/leaderboard")
async def leaderboard(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("""
        SELECT handle, display_name, total_contributions, total_reuse_count, reputation_score
        FROM contributors
        ORDER BY total_reuse_count DESC, total_contributions DESC
        LIMIT 20
    """))
    rows = result.fetchall()
    return [
        {"handle": r[0], "display_name": r[1], "total_contributions": r[2],
         "total_reuse_count": r[3], "reputation_score": round(r[4], 2)}
        for r in rows
    ]
