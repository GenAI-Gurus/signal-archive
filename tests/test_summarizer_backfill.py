import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_backfill_updates_all_canonicals():
    """Backfill fetches canonical rows, generates summary for each, and writes back."""
    from batch.backfill import run

    canonical_rows = [
        ("uuid-1", "How does TLS work?"),
        ("uuid-2", "What is eventual consistency?"),
    ]
    short_answer_rows_1 = [("TLS uses asymmetric crypto.",), ("Certificates validate identity.",)]
    short_answer_rows_2 = [("Systems may disagree temporarily.",)]

    select_canonicals = MagicMock()
    select_canonicals.fetchall.return_value = canonical_rows

    sa_result_1 = MagicMock()
    sa_result_1.fetchall.return_value = short_answer_rows_1

    sa_result_2 = MagicMock()
    sa_result_2.fetchall.return_value = short_answer_rows_2

    update_result = MagicMock()

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[
        select_canonicals,
        sa_result_1, update_result,
        sa_result_2, update_result,
    ])
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_engine = AsyncMock()
    mock_engine.dispose = AsyncMock()

    with patch("batch.backfill.create_async_engine", return_value=mock_engine), \
         patch("batch.backfill.sessionmaker", return_value=MagicMock(return_value=mock_session)), \
         patch("batch.backfill.synthesize_summary", new=AsyncMock(return_value="A synthesized summary.")), \
         patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://fake/db"}):
        count = await run()

    assert count == 2
    mock_session.commit.assert_called_once()
    mock_engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_backfill_skips_canonicals_with_no_artifacts():
    """Canonicals with no artifacts (empty short_answers) get an empty summary and are still updated."""
    from batch.backfill import run

    canonical_rows = [("uuid-3", "What is chaos engineering?")]

    select_canonicals = MagicMock()
    select_canonicals.fetchall.return_value = canonical_rows

    sa_result_empty = MagicMock()
    sa_result_empty.fetchall.return_value = []

    update_result = MagicMock()

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[select_canonicals, sa_result_empty, update_result])
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_engine = AsyncMock()
    mock_engine.dispose = AsyncMock()

    with patch("batch.backfill.create_async_engine", return_value=mock_engine), \
         patch("batch.backfill.sessionmaker", return_value=MagicMock(return_value=mock_session)), \
         patch("batch.backfill.synthesize_summary", new=AsyncMock(return_value="")), \
         patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://fake/db"}):
        count = await run()

    assert count == 1
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_backfill_handles_empty_table():
    """Returns 0 when canonical_questions table is empty."""
    from batch.backfill import run

    select_canonicals = MagicMock()
    select_canonicals.fetchall.return_value = []

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=select_canonicals)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_engine = AsyncMock()
    mock_engine.dispose = AsyncMock()

    with patch("batch.backfill.create_async_engine", return_value=mock_engine), \
         patch("batch.backfill.sessionmaker", return_value=MagicMock(return_value=mock_session)), \
         patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://fake/db"}):
        count = await run()

    assert count == 0
    mock_session.commit.assert_called_once()
    mock_engine.dispose.assert_called_once()
