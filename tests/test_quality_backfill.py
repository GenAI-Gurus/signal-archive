import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("OPENAI_API_KEY", "x")
os.environ.setdefault("API_KEY_SALT", "x")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("FERNET_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
os.environ.setdefault("RESEND_API_KEY", "")


@pytest.mark.asyncio
async def test_backfill_scores_all_unscored():
    """Backfill fetches artifacts with no quality_score, computes, and writes back."""
    from batch.quality_backfill import run

    artifact_rows = [
        ("uuid-1", ["a.com", "b.com"], "Short A.", " ".join(["word"] * 1000)),
        ("uuid-2", ["x.com"] * 15, "Short B.", " ".join(["word"] * 2000)),
    ]
    select_result = MagicMock()
    select_result.fetchall.return_value = artifact_rows

    update_result = MagicMock()

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[
        select_result,
        update_result,
        update_result,
    ])
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_engine = AsyncMock()
    mock_engine.dispose = AsyncMock()

    with patch("batch.quality_backfill.create_async_engine", return_value=mock_engine), \
         patch("batch.quality_backfill.sessionmaker", return_value=MagicMock(return_value=mock_session)), \
         patch("batch.quality_backfill.compute_quality_score", new=AsyncMock(return_value=55.0)), \
         patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://fake/db"}):
        count = await run()

    assert count == 2
    mock_session.commit.assert_called_once()
    mock_engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_backfill_skips_when_all_scored():
    """Returns 0 when all artifacts already have a quality_score."""
    from batch.quality_backfill import run

    select_result = MagicMock()
    select_result.fetchall.return_value = []

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=select_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_engine = AsyncMock()
    mock_engine.dispose = AsyncMock()

    with patch("batch.quality_backfill.create_async_engine", return_value=mock_engine), \
         patch("batch.quality_backfill.sessionmaker", return_value=MagicMock(return_value=mock_session)), \
         patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://fake/db"}):
        count = await run()

    assert count == 0
    mock_session.commit.assert_called_once()
