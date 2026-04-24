#!/usr/bin/env python3
"""
Recomputes reputation scores for all contributors.
Designed to run on a schedule (e.g., Fly.io scheduled machine, daily).
"""
import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(__file__))
from scorer import compute_reputation_score


async def run() -> int:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    try:
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            result = await session.execute(text("""
                SELECT
                    c.id,
                    c.total_contributions,
                    c.total_reuse_count,
                    COALESCE(SUM(ra.useful_count), 0)           AS useful_flags,
                    COALESCE(SUM(ra.stale_count), 0)            AS stale_flags,
                    COALESCE(SUM(ra.weakly_sourced_count), 0)   AS weakly_sourced_flags,
                    COALESCE(SUM(ra.wrong_count), 0)            AS wrong_flags
                FROM contributors c
                LEFT JOIN research_artifacts ra ON ra.contributor_id = c.id
                GROUP BY c.id, c.total_contributions, c.total_reuse_count
            """))
            rows = result.fetchall()

            updated = 0
            for row in rows:
                contrib_id, total_contributions, total_reuse_count, useful, stale, weak, wrong = row
                score = compute_reputation_score(
                    total_contributions=int(total_contributions),
                    total_reuse_count=int(total_reuse_count),
                    useful_flags=int(useful),
                    stale_flags=int(stale),
                    weakly_sourced_flags=int(weak),
                    wrong_flags=int(wrong),
                )
                await session.execute(
                    text("UPDATE contributors SET reputation_score = :score WHERE id = :id"),
                    {"score": score, "id": str(contrib_id)},
                )
                updated += 1

            await session.commit()
            print(f"[reputation] Updated {updated} contributor(s).")
            return updated
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
