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

    mock_result = MagicMock()
    mock_result.fetchall.return_value = fake_rows

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
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
    # execute called once for SELECT + twice for UPDATE (one per contributor)
    assert mock_session.execute.call_count == 3
    mock_session.commit.assert_called_once()
