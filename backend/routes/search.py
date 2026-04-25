from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Literal, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db
from embeddings import get_embedding
from schemas import SearchResult
from auth import get_optional_jwt

router = APIRouter(tags=["search"])

MIN_SIMILARITY = 0.5
CANDIDATE_POOL = 50

@router.get("", response_model=list[SearchResult])
async def search_archive(
    q: str = Query(..., min_length=3, max_length=1000),
    limit: int = Query(default=5, ge=1, le=20),
    sort: Literal["relevance", "quality", "reuse"] = Query(default="relevance"),
    db: AsyncSession = Depends(get_db),
    jwt: Optional[dict] = Depends(get_optional_jwt),
):
    embedding = await get_embedding(q)
    if not all(isinstance(v, (int, float)) for v in embedding):
        raise HTTPException(status_code=502, detail="Invalid embedding returned by upstream service")
    vector_literal = f"[{','.join(str(float(v)) for v in embedding)}]"

    if sort == "relevance":
        result = await db.execute(text("""
            SELECT id, title, synthesized_summary,
                   1 - (embedding <=> CAST(:vec AS vector)) AS similarity,
                   artifact_count, reuse_count, last_updated_at
            FROM canonical_questions
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :limit
        """), {"vec": vector_literal, "limit": limit})
    elif sort == "quality":
        result = await db.execute(text("""
            WITH candidates AS (
                SELECT id, title, synthesized_summary,
                       1 - (embedding <=> CAST(:vec AS vector)) AS similarity,
                       artifact_count, reuse_count, last_updated_at
                FROM canonical_questions
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:vec AS vector)
                LIMIT :pool
            )
            SELECT c.id, c.title, c.synthesized_summary, c.similarity,
                   c.artifact_count, c.reuse_count, c.last_updated_at,
                   COALESCE(AVG(ra.quality_score), 0) AS avg_quality
            FROM candidates c
            LEFT JOIN research_artifacts ra ON ra.canonical_question_id = c.id
            WHERE c.similarity >= :min_sim
            GROUP BY c.id, c.title, c.synthesized_summary, c.similarity,
                     c.artifact_count, c.reuse_count, c.last_updated_at
            ORDER BY avg_quality DESC
            LIMIT :limit
        """), {"vec": vector_literal, "pool": CANDIDATE_POOL, "min_sim": MIN_SIMILARITY, "limit": limit})
    else:  # reuse
        result = await db.execute(text("""
            WITH candidates AS (
                SELECT id, title, synthesized_summary,
                       1 - (embedding <=> CAST(:vec AS vector)) AS similarity,
                       artifact_count, reuse_count, last_updated_at
                FROM canonical_questions
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:vec AS vector)
                LIMIT :pool
            )
            SELECT id, title, synthesized_summary, similarity,
                   artifact_count, reuse_count, last_updated_at
            FROM candidates
            WHERE similarity >= :min_sim
            ORDER BY reuse_count DESC
            LIMIT :limit
        """), {"vec": vector_literal, "pool": CANDIDATE_POOL, "min_sim": MIN_SIMILARITY, "limit": limit})

    rows = result.fetchall()
    authenticated = jwt is not None
    return [
        SearchResult(
            canonical_question_id=row[0],
            title=row[1],
            synthesized_summary=row[2] if authenticated else None,
            similarity=round(float(row[3]), 4),
            artifact_count=row[4],
            reuse_count=row[5],
            last_updated_at=row[6],
        )
        for row in rows
    ]
