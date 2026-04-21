from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db
from embeddings import get_embedding
from schemas import SearchResult

router = APIRouter(tags=["search"])

@router.get("", response_model=list[SearchResult])
async def search_archive(
    q: str = Query(..., min_length=3),
    limit: int = Query(default=5, le=20),
    db: AsyncSession = Depends(get_db),
):
    embedding = await get_embedding(q)
    if not all(isinstance(v, (int, float)) for v in embedding):
        raise ValueError("Invalid embedding returned")
    vector_literal = f"[{','.join(str(float(v)) for v in embedding)}]"
    result = await db.execute(text(f"""
        SELECT
            id,
            title,
            synthesized_summary,
            1 - (embedding <=> '{vector_literal}'::vector) AS similarity,
            artifact_count,
            reuse_count,
            last_updated_at
        FROM canonical_questions
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> '{vector_literal}'::vector
        LIMIT :limit
    """), {"limit": limit})
    rows = result.fetchall()
    return [
        SearchResult(
            canonical_question_id=row[0],
            title=row[1],
            synthesized_summary=row[2],
            similarity=round(float(row[3]), 4),
            artifact_count=row[4],
            reuse_count=row[5],
            last_updated_at=row[6],
        )
        for row in rows
    ]
