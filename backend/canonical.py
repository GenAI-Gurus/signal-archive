import logging
import uuid
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from models import CanonicalQuestion
from summarizer import synthesize_summary

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.88


async def find_or_create_canonical(
    db: AsyncSession,
    question: str,
    embedding: list[float],
    summary: str,
) -> tuple[UUID, bool]:
    """Return (canonical_question_id, was_created)."""
    if not all(isinstance(v, (int, float)) for v in embedding):
        raise ValueError("Embedding must contain only numeric values")
    vector_literal = f"[{','.join(str(float(v)) for v in embedding)}]"
    result = await db.execute(text(f"""
        SELECT id, title, 1 - (embedding <=> '{vector_literal}'::vector) AS similarity
        FROM canonical_questions
        WHERE 1 - (embedding <=> '{vector_literal}'::vector) > :threshold
        ORDER BY similarity DESC
        LIMIT 1
    """), {"threshold": SIMILARITY_THRESHOLD})
    rows = result.fetchall()

    if rows:
        canonical_id = rows[0][0]
        canonical_title = rows[0][1]

        art_result = await db.execute(
            text(
                "SELECT short_answer FROM research_artifacts"
                " WHERE canonical_question_id = :cid"
                " ORDER BY created_at DESC LIMIT 10"
            ),
            {"cid": str(canonical_id)},
        )
        existing_answers = [r[0] for r in art_result.fetchall()]
        all_answers = [summary] + existing_answers

        try:
            new_summary = await synthesize_summary(canonical_title, all_answers)
            await db.execute(
                text(
                    "UPDATE canonical_questions"
                    " SET last_updated_at = NOW(),"
                    "     artifact_count = artifact_count + 1,"
                    "     synthesized_summary = :summary"
                    " WHERE id = :id"
                ),
                {"summary": new_summary, "id": canonical_id},
            )
        except Exception:
            logger.warning(
                "synthesize_summary failed for canonical %s, falling back to count-only update",
                canonical_id,
                exc_info=True,
            )
            await db.execute(
                text(
                    "UPDATE canonical_questions"
                    " SET last_updated_at = NOW(),"
                    "     artifact_count = artifact_count + 1"
                    " WHERE id = :id"
                ),
                {"id": canonical_id},
            )
        return canonical_id, False

    canonical = CanonicalQuestion(
        id=uuid.uuid4(),
        title=question,
        synthesized_summary=summary,
        embedding=embedding,
        artifact_count=1,
    )
    db.add(canonical)
    await db.flush()
    return canonical.id, True
