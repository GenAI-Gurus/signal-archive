#!/usr/bin/env python3
"""
Computes quality_score for all research_artifacts that don't have one yet.
Run once after deploying the quality scorer, then as needed.
"""
import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from quality import compute_quality_score  # noqa: E402


async def run() -> int:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    try:
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            result = await session.execute(text(
                "SELECT id, source_domains, short_answer, full_body"
                " FROM research_artifacts"
                " WHERE quality_score IS NULL"
                " ORDER BY created_at"
            ))
            rows = result.fetchall()

            updated = 0
            for artifact_id, source_domains, short_answer, full_body in rows:
                score = await compute_quality_score(
                    source_domains=source_domains or [],
                    full_body=full_body,
                    short_answer=short_answer,
                )
                await session.execute(
                    text(
                        "UPDATE research_artifacts"
                        " SET quality_score = :score"
                        " WHERE id = :id"
                    ),
                    {"score": score, "id": str(artifact_id)},
                )
                updated += 1

            await session.commit()
            print(f"[quality] Scored {updated} artifact(s).")
            return updated
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
