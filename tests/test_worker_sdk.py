import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from worker_sdk import ArchiveClient, SearchMatch

@pytest.mark.asyncio
async def test_search_returns_match_list():
    fake_results = [{
        "canonical_question_id": "cq-id-1",
        "title": "Best vector databases 2025",
        "synthesized_summary": "Overview of top vector DBs",
        "similarity": 0.94,
        "artifact_count": 3,
        "reuse_count": 7,
        "last_updated_at": "2026-04-01T00:00:00"
    }]
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.json.return_value = fake_results
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        client = ArchiveClient()
        results = await client.search("best vector databases")

    assert len(results) == 1
    assert isinstance(results[0], SearchMatch)
    assert results[0].similarity == 0.94

@pytest.mark.asyncio
async def test_search_returns_empty_on_no_results():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        client = ArchiveClient()
        results = await client.search("very obscure topic with no matches")

    assert results == []
