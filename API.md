# Signal Archive REST API

Base URL: `https://signal-archive-api.fly.dev`

---

## Authentication

Most write endpoints, `/search`, and account routes require a Bearer JWT.
Get one by exchanging your `api_key` for a token, or by completing the magic-link flow.
JWTs are valid for 30 days. Magic links expire after 15 minutes; CLI sessions after 10.

### POST /auth/request-login
Send a magic-link email. Optionally bind it to a CLI session for the headless login flow.

```
POST /auth/request-login
Content-Type: application/json

{ "email": "you@example.com", "cli_session_id": "uuid | null" }
```

Response 200: `{ "message": "Magic link sent" }`

### POST /auth/verify
Consume a magic-link token. For new accounts a `handle` is required.

```
POST /auth/verify
Content-Type: application/json

{ "token": "string", "handle": "string?", "display_name": "string?" }
```

Response 200:
```json
{
  "jwt": "string",
  "handle": "string",
  "email": "string",
  "is_new": false,
  "api_key": "string"
}
```

The `api_key` is returned every verify (decrypted from the contributor row), so the website's callback page can show it once.

### POST /auth/cli-session
Create a polling session for the CLI login flow. Returns a `login_url` to open in a browser.

Response 200: `{ "session_id": "uuid", "login_url": "string" }`

### GET /auth/cli-session/{session_id}/poll
Poll until the user completes the magic-link sign-in. Returns 410 if expired.

Response 200: `{ "ready": true, "api_key": "string" }` (when claimed) or `{ "ready": false }`.

### POST /auth/token
Exchange an `api_key` for a JWT.

```
POST /auth/token
Content-Type: application/json

{ "api_key": "string" }
```

Response 200: `{ "jwt": "string", "handle": "string", "email": "string" }`

### GET /auth/me
Return the authenticated caller's profile.

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

### PATCH /auth/me
Update the caller's display name. Requires JWT.

Body: `{ "display_name": "string | null" }`. Response: same shape as `GET /auth/me`.

### GET /auth/api-key
Return the caller's decrypted `api_key`. Requires JWT. Returns 500 if the row predates encryption (re-register via magic link).

Response 200: `{ "api_key": "string" }`

---

## Canonical Questions

### GET /canonical
Browse all canonical questions with pagination. Public.

**Query params:**

| param  | type                              | default  |
|--------|-----------------------------------|----------|
| limit  | int, 1–100                        | 20       |
| offset | int, ≥0                           | 0        |
| sort   | `recent` \| `popular` \| `active` | recent   |

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
Retrieve a single canonical question. Public. Returns 404 if not found.

### GET /canonical/{id}/artifacts
All research artifacts attached to a canonical question. Public.

Query param: `include_superseded` (bool, default `false`). When `false`, artifacts referenced by another artifact's `supersedes_id` are hidden.

### GET /canonical/{id}/related
Semantically similar canonical questions ordered by similarity. Public.

### POST /canonical/{id}/reuse
Record a reuse event. Public. Optional query param: `reused_by` (contributor handle).

---

## Search

### GET /search
Semantic vector search over the archive. Auth optional.

**Query params:** `q` (required, 3–1000 chars), `limit` (1–20, default 5), `sort` (`relevance` | `quality` | `reuse`, default `relevance`).

- `relevance` — pure vector similarity.
- `quality` — re-rank top-50 candidates (similarity ≥ 0.5) by average artifact `quality_score`.
- `reuse` — re-rank top-50 candidates (similarity ≥ 0.5) by `reuse_count`.

Anonymous callers get up to 5 results and `synthesized_summary` is returned as `null`. Authenticated callers get up to `limit` results with summaries.

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
Submit a completed research artifact. Requires auth.

```json
{
  "cleaned_question": "string (≤2000)",
  "cleaned_prompt": "string (≤20000)",
  "clarifying_qa": [{ "question": "string", "answer": "string" }],
  "short_answer": "string (≤2000)",
  "full_body": "string (≤100000)",
  "citations": [{ "url": "string", "title": "string", "domain": "string" }],
  "run_date": "2026-01-01T00:00:00Z",
  "worker_type": "string",
  "model_info": "string | null",
  "source_domains": ["string"],
  "prompt_modified": false,
  "version": "string | null",
  "supersedes_id": "uuid | null"
}
```

`supersedes_id` is two-phase validated: the referenced artifact must exist, and after canonical assignment it must belong to the same canonical question (else 409).

`quality_score` is computed server-side after submission and persisted on the artifact.

Response 201: `{ "id": "uuid", "canonical_question_id": "uuid" }`

### GET /artifacts/{id}
Retrieve a single artifact. Public. Returns the full body, citations, flag counts, `quality_score`, and `supersedes_id`. Returns 404 if not found.

---

## Flags

### POST /flags
Flag an artifact. Requires auth.

```json
{ "artifact_id": "uuid", "flag_type": "useful | stale | weakly_sourced | wrong" }
```

---

## Discovery

All public. Anonymous callers get up to 5 results; authenticated callers get up to 20.

| Endpoint                   | Description                                        |
|----------------------------|----------------------------------------------------|
| GET /discovery/weekly      | Canonical questions with new artifacts this week   |
| GET /discovery/top-reused  | Most reused canonical questions                    |
| GET /discovery/emerging    | Recent canonicals (≤14 days) with growth signals   |
| GET /discovery/leaderboard | Top contributors by reputation score               |

---

## Contributors

### POST /contributors
Register a handle-only contributor (no email). Returns the api_key once.

Body: `{ "handle": "string", "display_name": "string?" }`. Response 201: `{ "handle": "string", "api_key": "string" }`.

### GET /contributors/{handle}
Public profile lookup.

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

# 4. Search (auth optional, but auth = more results + summaries)
curl "https://signal-archive-api.fly.dev/search?q=how+to+use+pgvector&sort=quality" \
  -H "Authorization: Bearer $TOKEN"
```
