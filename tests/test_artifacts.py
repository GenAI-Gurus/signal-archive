import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from main import app
from database import get_db

VALID_SUBMISSION = {
    "cleaned_question": "What are the best vector databases in 2024?",
    "cleaned_prompt": "Research and compare the top vector databases available in 2024.",
    "short_answer": "The top vector databases are Pinecone, Weaviate, and pgvector.",
    "full_body": "## Vector Database Comparison\n\nDetailed analysis...",
    "citations": [{"url": "https://example.com", "title": "Vector DB Guide", "domain": "example.com"}],
    "run_date": "2026-04-01T12:00:00Z",
    "worker_type": "claude_code",
    "source_domains": ["example.com"],
    "prompt_modified": False,
}

@pytest.mark.asyncio
async def test_submit_artifact_without_api_key_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/artifacts", json=VALID_SUBMISSION)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_submit_artifact_with_valid_key_returns_201():
    import uuid
    fake_embedding = [0.1] * 1536
    fake_contributor = MagicMock()
    fake_contributor.id = uuid.uuid4()
    fake_contributor.handle = "alice"

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.execute = AsyncMock()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("routes.artifacts.get_embedding", new_callable=AsyncMock, return_value=fake_embedding), \
             patch("routes.artifacts.find_or_create_canonical", new_callable=AsyncMock, return_value=(str(uuid.uuid4()), True)), \
             patch("routes.artifacts.get_contributor_from_key", new_callable=AsyncMock, return_value=fake_contributor):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/artifacts",
                    json=VALID_SUBMISSION,
                    headers={"X-API-Key": "test-key"}
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "canonical_question_id" in data


@pytest.mark.asyncio
async def test_artifact_response_schema_includes_supersedes_id():
    """ArtifactResponse schema has supersedes_id field (None when not set)."""
    from schemas import ArtifactResponse
    import uuid
    from datetime import datetime, timezone

    resp = ArtifactResponse(
        id=uuid.uuid4(),
        canonical_question_id=uuid.uuid4(),
        contributor_handle=None,
        cleaned_question="q",
        short_answer="a",
        full_body="body",
        citations=[],
        run_date=datetime.now(timezone.utc),
        worker_type="test",
        source_domains=[],
        prompt_modified=False,
        useful_count=0,
        stale_count=0,
        weakly_sourced_count=0,
        wrong_count=0,
        created_at=datetime.now(timezone.utc),
        supersedes_id=None,
    )
    assert resp.supersedes_id is None
    assert hasattr(resp, "supersedes_id")


@pytest.mark.asyncio
async def test_artifact_submit_schema_accepts_supersedes_id():
    """ArtifactSubmit schema accepts an optional supersedes_id UUID."""
    from schemas import ArtifactSubmit
    import uuid
    from datetime import datetime, timezone

    target_id = uuid.uuid4()
    sub = ArtifactSubmit(
        cleaned_question="What is X?",
        cleaned_prompt="Research X.",
        short_answer="X is Y.",
        full_body="Details.",
        citations=[],
        run_date=datetime.now(timezone.utc),
        worker_type="test",
        source_domains=[],
        prompt_modified=False,
        supersedes_id=target_id,
    )
    assert sub.supersedes_id == target_id


@pytest.mark.asyncio
async def test_submit_with_valid_supersedes_id_returns_201():
    """A supersedes_id that belongs to the same canonical is accepted."""
    import uuid
    fake_embedding = [0.1] * 1536
    fake_contributor = MagicMock()
    fake_contributor.id = uuid.uuid4()
    canonical_id = str(uuid.uuid4())
    superseded_id = str(uuid.uuid4())

    existing_artifact = MagicMock()
    existing_artifact.id = superseded_id

    # execute call order after mocked helpers:
    # 1. validate supersedes_id → returns existing_artifact
    # 2. UPDATE contributors
    # 3. (quality score) UPDATE research_artifacts
    validate_result = MagicMock()
    validate_result.scalar_one_or_none = MagicMock(return_value=existing_artifact)

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[validate_result, validate_result, AsyncMock(), AsyncMock()])

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("routes.artifacts.get_embedding", new_callable=AsyncMock, return_value=fake_embedding), \
             patch("routes.artifacts.find_or_create_canonical", new_callable=AsyncMock, return_value=(canonical_id, True)), \
             patch("routes.artifacts.get_contributor_from_key", new_callable=AsyncMock, return_value=fake_contributor), \
             patch("routes.artifacts.compute_quality_score", new_callable=AsyncMock, return_value=70.0):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/artifacts",
                    json={**VALID_SUBMISSION, "supersedes_id": superseded_id},
                    headers={"X-API-Key": "test-key"},
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_submit_with_invalid_supersedes_id_returns_422():
    """A supersedes_id that does not belong to the same canonical is rejected with 422."""
    import uuid
    fake_embedding = [0.1] * 1536
    fake_contributor = MagicMock()
    fake_contributor.id = uuid.uuid4()
    canonical_id = str(uuid.uuid4())
    wrong_artifact_id = str(uuid.uuid4())

    # Lookup returns None — the artifact is not in this canonical
    validate_result = MagicMock()
    validate_result.scalar_one_or_none = MagicMock(return_value=None)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=validate_result)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("routes.artifacts.get_embedding", new_callable=AsyncMock, return_value=fake_embedding), \
             patch("routes.artifacts.find_or_create_canonical", new_callable=AsyncMock, return_value=(canonical_id, True)), \
             patch("routes.artifacts.get_contributor_from_key", new_callable=AsyncMock, return_value=fake_contributor):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/artifacts",
                    json={**VALID_SUBMISSION, "supersedes_id": wrong_artifact_id},
                    headers={"X-API-Key": "test-key"},
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "supersedes_id" in response.json()["detail"].lower()
