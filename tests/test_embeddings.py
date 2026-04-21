import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_get_embedding_returns_list_of_floats():
    fake_vector = [0.1] * 1536
    with patch("embeddings.client.embeddings.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value.data = [type("obj", (), {"embedding": fake_vector})()]
        from embeddings import get_embedding
        result = await get_embedding("what is the best python ORM?")
    assert isinstance(result, list)
    assert len(result) == 1536
    assert all(isinstance(v, float) for v in result)
