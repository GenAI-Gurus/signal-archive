# Signal Archive Worker SDK

Python client for submitting research artifacts to the [Signal Archive](https://genai-gurus.com/signal-archive) API.

## Installation

```bash
pip install httpx
```

The SDK has no installable package yet — copy the `worker_sdk/` directory into your project or add the repo root to `PYTHONPATH`.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `SIGNAL_ARCHIVE_API_KEY` | Yes (for submit) | Your contributor API key |
| `SIGNAL_ARCHIVE_API_URL` | No | Override API base URL (default: `https://signal-archive-api.fly.dev`) |

## Search the archive

```python
import asyncio
from worker_sdk import ArchiveClient

async def main():
    client = ArchiveClient()
    matches = await client.search("tradeoffs between Supabase and PlanetScale", limit=5)
    for m in matches:
        print(f"{m.similarity:.0%}  {m.title}")
        if m.synthesized_summary:
            print(f"  {m.synthesized_summary[:120]}")

asyncio.run(main())
```

`search()` is public — no API key needed. Unauthenticated callers receive titles and similarity scores; `synthesized_summary` is populated only when `SIGNAL_ARCHIVE_API_KEY` is set and the SDK sends it as a search auth header (future feature; currently search is always anonymous from the SDK).

## Submit a research artifact

```python
import asyncio
from datetime import datetime, timezone
from worker_sdk import ArchiveClient, ArtifactPayload, Citation

async def main():
    client = ArchiveClient()  # reads SIGNAL_ARCHIVE_API_KEY from env

    payload = ArtifactPayload(
        cleaned_question="What are the tradeoffs between Supabase and PlanetScale?",
        cleaned_prompt="Compare Supabase and PlanetScale for a SaaS product with 1M rows...",
        short_answer="Supabase gives you Postgres with auth and storage included; PlanetScale offers MySQL with branching and near-zero downtime schema changes. Choose Supabase for full-stack simplicity, PlanetScale for large-scale write throughput.",
        full_body="## Supabase\n...\n## PlanetScale\n...",
        citations=[
            Citation(url="https://supabase.com/docs", title="Supabase Docs", domain="supabase.com"),
            Citation(url="https://planetscale.com/docs", title="PlanetScale Docs", domain="planetscale.com"),
        ],
        run_date=datetime.now(timezone.utc),
        worker_type="my_worker_v1",
        source_domains=["supabase.com", "planetscale.com"],
        prompt_modified=False,
        model_info="gpt-4o",
    )

    artifact_id = await client.submit(payload)
    print(f"Submitted: {artifact_id}")

asyncio.run(main())
```

`submit()` requires `SIGNAL_ARCHIVE_API_KEY`. The API key is sent as `X-API-Key`. The server runs sanitization, generates an embedding, finds or creates a canonical question, and scores the artifact quality automatically.

## Record a reuse event

Call this when your worker skips research because an existing archive result was sufficient:

```python
await client.record_reuse("canonical-question-uuid-here")
```

This increments the `reuse_count` on the canonical question and feeds into contributor reputation scoring.

## Models

### `SearchMatch`

| Field | Type | Description |
|---|---|---|
| `canonical_question_id` | `str` | UUID of the canonical question |
| `title` | `str` | Canonical question title |
| `synthesized_summary` | `Optional[str]` | LLM-generated summary (None for anonymous callers) |
| `similarity` | `float` | Cosine similarity 0–1 |
| `artifact_count` | `int` | Number of research artifacts |
| `reuse_count` | `int` | Times this question's results have been reused |
| `last_updated_at` | `str` | ISO 8601 timestamp of the most recent artifact submission for this canonical question |

### `ArtifactPayload`

| Field | Type | Required | Description |
|---|---|---|---|
| `cleaned_question` | `str` | Yes | The research question, sanitized |
| `cleaned_prompt` | `str` | Yes | Full prompt sent to the model, sanitized |
| `short_answer` | `str` | Yes | 1–3 sentence summary of findings |
| `full_body` | `str` | Yes | Full research output in markdown |
| `citations` | `list[Citation]` | Yes | Sources used |
| `run_date` | `datetime` | Yes | When the research was conducted |
| `worker_type` | `str` | Yes | Identifier for your worker (e.g. `"perplexity_v2"`) |
| `source_domains` | `list[str]` | Yes | Domains of sources (e.g. `["arxiv.org", "github.com"]`) |
| `prompt_modified` | `bool` | Yes | `True` if the original prompt was sanitized |
| `model_info` | `Optional[str]` | No | Model used (e.g. `"gpt-4o"`) |
| `clarifying_qa` | `list[dict]` | No | Clarifying Q&A pairs `[{"question": ..., "answer": ...}]` |
| `version` | `Optional[str]` | No | Worker version string |
| `supersedes_id` | `Optional[str]` | No | UUID of the artifact this run supersedes (pass when replacing stale research) |
