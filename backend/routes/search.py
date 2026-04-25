from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db
from embeddings import get_embedding
from schemas import SearchResult
from auth import get_optional_jwt

router = APIRouter(tags=["search"])

@router.get("", response_model=list[SearchResult])
async def search_archive(
    q: str = Query(..., min_length=3, max_length=1000),
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    jwt: Optional[dict] = Depends(get_optional_jwt),
):
    embedding = await get_embedding(q)
    if not all(isinstance(v, (int, float)) for v in embedding):
        raise HTTPException(status_code=502, detail="Invalid embedding returned by upstream service")
    vector_literal = f"[{','.join(str(float(v)) for v in embedding)}]"
    result = await db.execute(text("""
        SELECT id, title, synthesized_summary,
               1 - (embedding <=> CAST(:vec AS vector)) AS similarity,
               artifact_count, reuse_count, last_updated_at
        FROM canonical_questions
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:vec AS vector)
        LIMIT :limit
    """), {"vec": vector_literal, "limit": limit})
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
