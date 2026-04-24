# Signal Archive REST API

Base URL: `https://signal-archive-api.fly.dev`

---

## Authentication

Most write endpoints and `/auth/me` require a Bearer JWT.
Exchange your `api_key` (shown after registration) for a token.
JWTs are valid for 30 days.

### POST /auth/token
Exchange an `api_key` for a JWT.

```
POST /auth/token
Content-Type: application/json

{ "api_key": "YOUR_API_KEY" }
```

Response 200:
```json
{ "jwt": "...", "handle": "alice", "email": "alice@example.com" }
```

### GET /auth/me
Return the authenticated caller's contributor profile.

```
GET /auth/me
Authorization: Bearer <jwt>
```

Response 200:
```json
{
  "handle": "alice",
  "display_name": "Alice",
  "email": "alice@example.com",
  "total_contributions": 12,
  "total_reuse_count": 47,
  "reputation_score": 3.9,
  "created_at": "2026-01-01T00:00:00Z"
}
```

---

## Canonical Questions

### GET /canonical
Browse all canonical questions with pagination.

**Query params:**

| param  | type                          | default  |
|--------|-------------------------------|----------|
| limit  | int, 1–100                    | 20       |
| offset | int, ≥0                       | 0        |
| sort   | `recent` \| `popular` \| `active` | recent |

- `recent` — newest first (by `last_updated_at`)
- `popular` — highest `reuse_count` first
- `active` — highest `artifact_count` first

Response 200:
```json
[
  {
    "id": "uuid",
    "title": "How do I configure pgvector on Supabase?",
    "synthesized_summary": "...",
    "artifact_count": 3,
    "reuse_count": 11,
    "created_at": "2026-01-01T00:00:00Z",
    "last_updated_at": "2026-04-01T00:00:00Z"
  }
]
```

### GET /canonical/{id}
Retrieve a single canonical question. Returns 404 if not found.

### GET /canonical/{id}/artifacts
All research artifacts attached to a canonical question.

### GET /canonical/{id}/related
Semantically similar canonical questions ordered by similarity score.

### POST /canonical/{id}/reuse
Record a reuse event. Optional query param: `reused_by` (contributor handle).

---

## Search

### GET /search
Semantic vector search over the archive. Requires auth.

**Query params:** `q` (required), `limit` (default 10)

Response 200 — list of `SearchResult`:
```json
[
  {
    "canonical_question_id": "uuid",
    "title": "string",
    "synthesized_summary": "string | null",
    "similarity": 0.92,
    "artifact_count": 3,
    "reuse_count": 7,
    "last_updated_at": "2026-04-01T00:00:00Z"
  }
]
```

---

## Artifacts

### POST /artifacts
Submit a completed research artifact to the archive. Requires auth.

```json
{
  "cleaned_question": "string",
  "cleaned_prompt": "string",
  "short_answer": "string",
  "full_body": "string",
  "citations": [{ "url": "string", "title": "string", "domain": "string" }],
  "run_date": "2026-01-01T00:00:00Z",
  "worker_type": "string",
  "model_info": "string | null",
  "source_domains": ["string"],
  "prompt_modified": false,
  "clarifying_qa": [{ "question": "string", "answer": "string" }],
  "version": "string | null"
}
```

Response 201: `{ "id": "uuid", "canonical_question_id": "uuid" }`

### GET /artifacts/{id}
Retrieve a single artifact. Public. Returns 404 if not found.

---

## Flags

### POST /flags
Flag an artifact. Requires auth.

```json
{ "artifact_id": "uuid", "flag_type": "useful | stale | weakly_sourced | wrong" }
```

---

## Discovery

All public, no auth required.

| Endpoint                  | Description                              |
|---------------------------|------------------------------------------|
| GET /discovery/weekly     | Recently added canonical questions       |
| GET /discovery/top-reused | Most reused canonical questions          |
| GET /discovery/emerging   | Questions with growing artifact counts   |
| GET /discovery/leaderboard| Top contributors by reputation score     |

---

## Quick Start

```bash
# 1. Get a JWT
TOKEN=$(curl -s -X POST https://signal-archive-api.fly.dev/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "YOUR_API_KEY"}' | jq -r .jwt)

# 2. Check your profile
curl https://signal-archive-api.fly.dev/auth/me \
  -H "Authorization: Bearer $TOKEN"

# 3. Browse the archive
curl "https://signal-archive-api.fly.dev/canonical?sort=popular&limit=10"

# 4. Search
curl "https://signal-archive-api.fly.dev/search?q=how+to+use+pgvector" \
  -H "Authorization: Bearer $TOKEN"
```
