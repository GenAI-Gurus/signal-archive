#!/usr/bin/env python3
"""
Regenerates synthesized_summary for all canonical questions.
Run once after deploying the summarizer feature, then as needed.
"""
import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Placeholder for synthesize_summary - will be set below or mocked in tests
async def synthesize_summary(question: str, short_answers: list[str]) -> str:
    """Placeholder - will be replaced with actual implementation or mocked."""
    raise NotImplementedError("Should be patched by tests or overwritten at module load")


# Try to import the real implementation from backend
try:
    _backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
    # Only add to sys.path if it's not already there
    if _backend_path not in sys.path:
        sys.path.insert(0, _backend_path)
    import importlib
    # Import from backend/summarizer.py directly
    _backend_summarizer = importlib.import_module('summarizer')
    synthesize_summary = _backend_summarizer.synthesize_summary
except Exception:
    # If import fails (e.g., missing env vars), the placeholder above will be used
    # Tests will patch this anyway
    pass


async def run() -> int:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    try:
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            result = await session.execute(text(
                "SELECT id, title FROM canonical_questions ORDER BY created_at"
            ))
            rows = result.fetchall()

            updated = 0
            for canonical_id, title in rows:
                sa_result = await session.execute(
                    text(
                        "SELECT short_answer FROM research_artifacts"
                        " WHERE canonical_question_id = :cid"
                        " ORDER BY created_at DESC LIMIT 10"
                    ),
                    {"cid": str(canonical_id)},
                )
                short_answers = [r[0] for r in sa_result.fetchall()]
                summary = await synthesize_summary(title, short_answers)
                await session.execute(
                    text(
                        "UPDATE canonical_questions"
                        " SET synthesized_summary = :summary"
                        " WHERE id = :id"
                    ),
                    {"summary": summary, "id": str(canonical_id)},
                )
                updated += 1

            await session.commit()
            print(f"[summarizer] Updated {updated} canonical question(s).")
            return updated
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
