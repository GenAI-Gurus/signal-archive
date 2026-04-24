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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from summarizer import synthesize_summary  # noqa: E402 — path must be set first


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
