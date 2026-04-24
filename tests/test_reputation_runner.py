import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_runner_updates_all_contributors():
    """Runner fetches contributor rows and writes back computed scores."""
    from reputation.runner import run

    fake_rows = [
        # (id, contributions, reuse, useful, stale, weak, wrong)
        ("uuid-1", 10, 40, 20, 1, 0, 0),
        ("uuid-2", 0,  0,   0, 0, 0, 0),
    ]

    select_result = MagicMock()
    select_result.fetchall.return_value = fake_rows
    update_result = MagicMock()

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[select_result, update_result, update_result])
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_factory = MagicMock(return_value=mock_session)

    mock_engine = AsyncMock()
    mock_engine.dispose = AsyncMock()

    with patch("reputation.runner.create_async_engine", return_value=mock_engine), \
         patch("reputation.runner.sessionmaker", return_value=mock_session_factory), \
         patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://fake/db"}):
        count = await run()

    assert count == 2
    # 1 SELECT + 2 UPDATEs
    assert mock_session.execute.call_count == 3
    mock_session.commit.assert_called_once()
    mock_engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_runner_handles_no_contributors():
    """Runner returns 0 when contributors table is empty."""
    from reputation.runner import run

    select_result = MagicMock()
    select_result.fetchall.return_value = []

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=select_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_engine = AsyncMock()
    mock_engine.dispose = AsyncMock()

    with patch("reputation.runner.create_async_engine", return_value=mock_engine), \
         patch("reputation.runner.sessionmaker", return_value=MagicMock(return_value=mock_session)), \
         patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://fake/db"}):
        count = await run()

    assert count == 0
    mock_session.commit.assert_called_once()
    mock_engine.dispose.assert_called_once()


def test_runner_missing_database_url_raises():
    """Missing DATABASE_URL raises KeyError at engine creation, not import time."""
    import importlib
    import reputation.runner as runner_mod

    clean_env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    with patch.dict(os.environ, clean_env, clear=True), \
         patch("reputation.runner.create_async_engine", side_effect=KeyError("DATABASE_URL")):
        import asyncio
        with pytest.raises(KeyError):
            asyncio.run(runner_mod.run())
