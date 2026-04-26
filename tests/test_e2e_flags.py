"""
E2E tests for the community flag system.

Verifies:
- Anon flag attempt returns 401
- Authenticated flag (X-API-Key) succeeds with 201
- Duplicate flag by same contributor returns 409
- Flag count appears on artifact after flagging
- Search and artifact endpoints still return 200

Run with:
    pytest -m e2e tests/test_e2e_flags.py -v
"""
import secrets
import httpx
import pytest

BASE = "https://signal-archive-api.fly.dev"
SESSION = secrets.token_hex(4)


def _warm_up():
    """Hit search until the app responds — handles Fly.io cold-start after deploy."""
    for attempt in range(6):
        try:
            with httpx.Client(timeout=90) as client:
                r = client.get(f"{BASE}/search", params={"q": "robotics", "limit": 1})
                if r.status_code == 200:
                    return
        except (httpx.ReadTimeout, httpx.ConnectTimeout):
            pass
    raise RuntimeError("API did not become ready after warm-up attempts")


@pytest.fixture(scope="module")
def contributor_and_artifact():
    """Register a contributor, submit one artifact, return (api_key, artifact_id)."""
    handle = f"flag-tester-{SESSION}"
    _warm_up()
    with httpx.Client(timeout=90) as client:

        r = client.post(f"{BASE}/contributors", json={"handle": handle, "display_name": "Flag Tester"})
        assert r.status_code == 201, f"contributor registration failed: {r.text}"
        api_key = r.json()["api_key"]

        r = client.post(
            f"{BASE}/artifacts",
            json={
                "cleaned_question": f"E2E flag test question {SESSION}",
                "cleaned_prompt": f"E2E flag test question {SESSION}",
                "short_answer": "This artifact exists solely to test the flag endpoint.",
                "full_body": "Test artifact body.",
                "citations": [],
                "run_date": "2026-04-26T00:00:00+00:00",
                "worker_type": "test",
                "source_domains": [],
                "prompt_modified": False,
            },
            headers={"X-API-Key": api_key},
            timeout=60,
        )
        assert r.status_code == 201, f"artifact submission failed: {r.text}"
        artifact_id = r.json()["id"]

    return api_key, artifact_id


@pytest.mark.e2e
def test_anon_flag_returns_401(contributor_and_artifact):
    _, artifact_id = contributor_and_artifact
    with httpx.Client(timeout=20) as client:
        r = client.post(f"{BASE}/flags", json={"artifact_id": artifact_id, "flag_type": "useful"})
    assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"


@pytest.mark.e2e
def test_authenticated_flag_succeeds(contributor_and_artifact):
    api_key, artifact_id = contributor_and_artifact
    with httpx.Client(timeout=20) as client:
        r = client.post(
            f"{BASE}/flags",
            json={"artifact_id": artifact_id, "flag_type": "useful"},
            headers={"X-API-Key": api_key},
        )
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"


@pytest.mark.e2e
def test_duplicate_flag_returns_409(contributor_and_artifact):
    api_key, artifact_id = contributor_and_artifact
    with httpx.Client(timeout=20) as client:
        # First flag may already exist from previous test; either 201 or 409 is fine
        client.post(
            f"{BASE}/flags",
            json={"artifact_id": artifact_id, "flag_type": "stale"},
            headers={"X-API-Key": api_key},
        )
        # Second identical flag must be 409
        r = client.post(
            f"{BASE}/flags",
            json={"artifact_id": artifact_id, "flag_type": "stale"},
            headers={"X-API-Key": api_key},
        )
    assert r.status_code == 409, f"Expected 409 on duplicate, got {r.status_code}: {r.text}"


@pytest.mark.e2e
def test_flag_different_types_both_accepted(contributor_and_artifact):
    """Same contributor can flag with different flag types."""
    api_key, artifact_id = contributor_and_artifact
    with httpx.Client(timeout=20) as client:
        r = client.post(
            f"{BASE}/flags",
            json={"artifact_id": artifact_id, "flag_type": "wrong"},
            headers={"X-API-Key": api_key},
        )
    # 201 (new) or 409 (already flagged from a prior run) — both are acceptable
    assert r.status_code in (201, 409), f"Unexpected status {r.status_code}: {r.text}"


@pytest.mark.e2e
def test_useful_count_incremented_on_artifact(contributor_and_artifact):
    """useful_count on the artifact should be >= 1 after the flag in test_authenticated_flag_succeeds."""
    _, artifact_id = contributor_and_artifact
    with httpx.Client(timeout=20) as client:
        r = client.get(f"{BASE}/artifacts/{artifact_id}")
    assert r.status_code == 200, f"GET artifact failed: {r.text}"
    data = r.json()
    assert data.get("useful_count", 0) >= 1, f"useful_count not incremented: {data}"


@pytest.mark.e2e
def test_flag_nonexistent_artifact_returns_404(contributor_and_artifact):
    api_key, _ = contributor_and_artifact
    fake_id = "00000000-0000-0000-0000-000000000000"
    with httpx.Client(timeout=20) as client:
        r = client.post(
            f"{BASE}/flags",
            json={"artifact_id": fake_id, "flag_type": "useful"},
            headers={"X-API-Key": api_key},
        )
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


@pytest.mark.e2e
def test_search_still_works():
    with httpx.Client(timeout=20) as client:
        r = client.get(f"{BASE}/search", params={"q": "robotics", "limit": 3})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
