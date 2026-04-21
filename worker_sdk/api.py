import os
import httpx
from .models import SearchMatch, ArtifactPayload

class ArchiveClient:
    def __init__(self):
        self.base_url = os.environ.get("SIGNAL_ARCHIVE_API_URL", "https://signal-archive-api.fly.dev")
        self.api_key = os.environ.get("SIGNAL_ARCHIVE_API_KEY", "")

    async def search(self, query: str, limit: int = 5) -> list[SearchMatch]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/search",
                params={"q": query, "limit": limit},
            )
            response.raise_for_status()
        return [SearchMatch(**item) for item in response.json()]

    async def submit(self, payload: ArtifactPayload) -> str:
        body = {
            "cleaned_question": payload.cleaned_question,
            "cleaned_prompt": payload.cleaned_prompt,
            "clarifying_qa": payload.clarifying_qa,
            "short_answer": payload.short_answer,
            "full_body": payload.full_body,
            "citations": [{"url": c.url, "title": c.title, "domain": c.domain} for c in payload.citations],
            "run_date": payload.run_date.isoformat(),
            "worker_type": payload.worker_type,
            "model_info": payload.model_info,
            "source_domains": payload.source_domains,
            "prompt_modified": payload.prompt_modified,
            "version": payload.version,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/artifacts",
                json=body,
                headers={"X-API-Key": self.api_key},
            )
            response.raise_for_status()
        return response.json()["id"]

    async def record_reuse(self, canonical_question_id: str) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{self.base_url}/canonical/{canonical_question_id}/reuse",
                params={"reused_by": "claude_code"},
            )
