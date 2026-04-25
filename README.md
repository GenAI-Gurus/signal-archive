# Signal Archive

**Public memory for deep research.** Stop repeating the same research across AI agent sessions.

Signal Archive is an open archive of sanitized research artifacts. Before your agent runs a deep research task, it checks whether the same question has already been answered. If it has, you can reuse the result. If not, the new research is automatically contributed back.

→ **[Browse the archive](https://genai-gurus.com/signal-archive)**

---

## Install

### Claude Code (plugin)

Run these three commands inside Claude Code:

```
/plugin marketplace add https://github.com/GenAI-Gurus/signal-archive
/plugin install signal-archive
/reload-plugins
```

That's it for read-only search. To enable automatic contribution, [register as a contributor](#register).

### Codex CLI (shell installer)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/GenAI-Gurus/signal-archive/main/install.sh)
```

This injects instructions into `~/.codex/instructions.md` so Codex searches the archive before research tasks and submits results automatically. The installer also works as a fallback for Claude Code environments without `/plugin` support.

Codex has no native hook system — the integration works by having Codex follow instructions to call `pre_task.py` and `post_task.py` as shell tools.

---

## How it works

**Before every research task**, Signal Archive searches the archive for similar existing research and shows you what's already been answered.

**After every research task**, if you've registered, the result is automatically sanitized and contributed to the public archive — so the next person with the same question benefits.

```
You: "What are the tradeoffs between Supabase and PlanetScale?"
                    │
         ┌──────────▼───────────┐
         │  Search archive      │  → Found 2 similar results (83% match)
         │  Sanitize prompt     │  → Removed implicit company refs
         └──────────┬───────────┘
                    │
         Claude researches and responds
                    │
         ┌──────────▼───────────┐
         │  Submit artifact     │  → Contributes to public archive
         └──────────────────────┘
```

All prompts are sanitized before submission — private company names, personal info, and credentials are stripped. Only public-safe research is accepted.

---

## Register

Two ways:

**Magic link (recommended)** — at the [Get Started page](https://genai-gurus.com/signal-archive/get-started), enter your email and click the link. Your `api_key` is shown once on the callback page.

**`/signal-archive:login`** — inside Claude Code, run the slash command. A browser opens, you sign in by email, and the plugin retrieves your `api_key` automatically via a CLI polling session.

**API-only (handle, no email)** — for headless setups:

```bash
curl -s -X POST https://signal-archive-api.fly.dev/contributors \
  -H "Content-Type: application/json" \
  -d '{"handle": "your-handle"}' | python3 -m json.tool
```

Whichever method you use, add the api_key to your shell profile:

```bash
echo 'export SIGNAL_ARCHIVE_API_KEY="your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

---

## What gets submitted

Only research artifacts that pass sanitization are accepted:

- ✅ Public figures by name (CEOs, researchers, public companies)
- ✅ Technical comparisons, market research, public API behavior
- ❌ Private individual names, contact info, credentials
- ❌ Implicit company references ("our product", "my team's stack") without substitution
- ❌ Relative time references ("this quarter") without explicit dates

The sanitizer runs locally before any data leaves your machine.

---

## Implemented features

### Core archive
- **Canonical question clustering** — semantic deduplication via pgvector. New submissions are matched to existing questions; a new canonical is created only when nothing similar exists. Threshold configurable via `SIMILARITY_THRESHOLD` env var (default 0.85).
- **Research artifacts** — full body (≤100k chars), short answer, citations (≤50), source domains, provenance (worker_type, run_date, model_info), clarifying Q&A (≤20 pairs).
- **Synthesized summaries** — when a canonical question accumulates multiple artifacts, gpt-4o-mini generates a 2–3 sentence synthesis. Summaries are **quality-weighted**: higher-`quality_score` artifacts get more influence in the synthesis. Shown on the browse page.
- **Related questions** — vector similarity surfaces the 5 most similar canonical questions on each artifact page.
- **Versioning at the data layer** — artifacts have `supersedes_id` (self-FK, two-phase validated: must exist + must be in the same canonical) and a free-form `version` string. The `/canonical/{id}/artifacts` endpoint hides superseded artifacts by default (`include_superseded=true` to opt in). UI does not yet surface a "supersede" action — see [Next best steps](#next-best-steps).

### Quality & trust
- **Automated quality scoring** (0–100, computed at submission time):
  - Source breadth: up to 40 pts (scaled to 20 unique domains)
  - Body depth: up to 30 pts (scaled to 2000 words)
  - Faithfulness: up to 30 pts (gpt-4o-mini checks whether the short answer reflects the full body — YES/PARTIAL/NO)
  - Score shown as a colored badge (High ≥70 / Medium ≥40 / Low <40) on each artifact card.
- **Search sort modes** — `relevance` (default), `quality` (avg artifact quality), or `reuse`. Non-relevance sorts apply a 0.5 similarity floor and re-rank a top-50 candidate pool.
- **Community flags** — readers flag artifacts as Useful, Stale, Weak sources, or Wrong. Counts persist on the artifact and feed contributor reputation. Flag state persists in `localStorage` so buttons stay disabled across reloads without needing an account.
- **Contributor reputation** — daily Fly.io scheduled job recomputes a 0–100 score from reuse ratio + community-flag ratio. Surfaced on the leaderboard.

### Identity & accounts
- **Magic-link sign-up + login** — email-based, no password. Magic links expire in 15 minutes. New accounts pick a handle on first verify; existing accounts get their `api_key` re-issued.
- **CLI login session** (`/auth/cli-session` + `/auth/cli-session/{id}/poll`) — `/signal-archive:login` opens a browser, you sign in by email, the CLI polls for completion (10-minute window), and your `api_key` lands in the terminal automatically.
- **API-key contributors** — register with handle only, no email. API key returned once and stored encrypted (Fernet).
- **JWT auth** — exchange `api_key` → `jwt` (HS256, 30 days). Used for `/search`, write endpoints, and account routes.
- **Account API** — `GET /auth/me`, `PATCH /auth/me` (display name), `GET /auth/api-key` (reveal decrypted key). Account page on the website wraps these.

### Website (Astro 4, GitHub Pages)
- **Browse** — paginated canonical questions, sortable by Recent / Popular / Active.
- **Artifact detail** — full body rendered as markdown, provenance card, community flags, related questions.
- **Search** — semantic search with JWT auth; anonymous callers get up to 5 results with summaries hidden.
- **Discovery** — emerging topics (recent canonicals with growth signals), researched-this-week, top-reused.
- **Leaderboard** — top contributors by reputation.
- **Account** — view stats, update display name, reveal API key.
- **Get Started, API Reference, About** pages.

### Agent integrations
- **Claude Code plugin** (`.claude-plugin/marketplace.json`, `hooks/hooks.json`) — hooks into `UserPromptSubmit` (pre-task search + sanitization) and `Stop` (post-task submission). Slash commands: `/signal-archive` (manual search), `/signal-archive:login` (browser-based magic-link login).
- **Codex CLI integration** — `install.sh` injects instructions into `~/.codex/instructions.md`; Codex calls `pre_task.py` and `post_task.py` as shell tools.
- Both integrations share the same `worker_sdk` and `sanitizer` packages. Artifacts are tagged with `worker_type` (`"claude_code"` or `"codex"`) for provenance.
- Reuse events are recorded (`POST /canonical/{id}/reuse`) when a pre-task search surfaces a ≥80% match. **Note:** as of this writing the recording is wired in `claude_code_integration/hooks/pre_task.py` (used by `install.sh`) and `codex_integration/hooks/pre_task.py`, but not in the top-level `hooks/pre_task.py` used by the `/plugin` install — see [Next best steps](#next-best-steps).

### Privacy & sanitization
- LLM-based sanitizer (`sanitizer/sanitizer.py`) runs locally via `subprocess` against whichever CLI is available (`claude` or `codex`). Returns a structured `SanitizationResult` (cleaned_prompt, was_modified, removed_categories, safe_to_submit, reason).
- Artifacts with `safe_to_submit=False` are skipped — research runs locally but is not contributed.

### Infrastructure
- FastAPI backend on Fly.io (rolling deploys), 2 machines, full async (SQLAlchemy async + asyncpg).
- Supabase Postgres + pgvector extension (1536-dim embeddings, `text-embedding-3-small`).
- Daily reputation batch via Fly.io scheduled machine (`reputation/runner.py`).
- One-off backfill scripts (`batch/backfill.py`, `batch/quality_backfill.py`).
- GitHub Actions → GitHub Pages for website deploys.
- Resend for transactional email (magic links).
- API keys hashed (SHA-256 + per-row salt) for lookup and Fernet-encrypted at rest for re-issue.

---

## Architecture

```
signal-archive/
├── .claude-plugin/           Plugin manifest + marketplace.json
├── hooks/                    Claude Code plugin hooks (used by /plugin install)
│   ├── pre_task.py           UserPromptSubmit — search + sanitize
│   ├── post_task.py          Stop — submit artifact
│   ├── login.py              CLI magic-link login (used by /signal-archive:login)
│   └── hooks.json            Plugin manifest pointing to the above
├── commands/                 Slash commands shipped by the plugin
│   ├── signal-archive.md     /signal-archive — manual search
│   └── login.md              /signal-archive:login — browser login
├── claude_code_integration/  Claude Code hooks bundled by install.sh (fallback path)
│   ├── hooks/                pre_task.py, post_task.py
│   └── setup.py              Writes settings.json hooks (project- or user-scope)
├── codex_integration/        Codex CLI integration (instruction injection)
│   ├── hooks/                pre_task.py, post_task.py (called as shell tools)
│   ├── instructions_template.md  Injected into ~/.codex/instructions.md
│   └── setup.py              Idempotent installer for ~/.codex/
├── install.sh                One-liner installer (Claude Code + Codex CLI auto-detect)
├── backend/                  FastAPI + SQLAlchemy, deployed on Fly.io
│   ├── routes/               artifacts, canonical, flags, search, auth, contributors, discovery
│   ├── auth.py               JWT, magic-link email, Fernet, hash_api_key
│   ├── canonical.py          Semantic dedup, quality-weighted synthesis prep
│   ├── quality.py            Source/depth/faithfulness scorer
│   ├── summarizer.py         gpt-4o-mini synthesis with quality weighting
│   ├── embeddings.py         text-embedding-3-small wrapper
│   ├── models.py             SQLAlchemy tables
│   └── schemas.py            Pydantic request/response models
├── batch/                    One-off backfill scripts
│   ├── backfill.py           Regenerate synthesized summaries
│   └── quality_backfill.py   Score artifacts missing quality_score
├── reputation/               Daily scheduled reputation scorer
│   ├── scorer.py             Pure function: contributions × reuse × flags → score
│   └── runner.py             Fly.io scheduled-machine entrypoint
├── sanitizer/                Local LLM-based prompt sanitizer
├── worker_sdk/               Async Python client (search, submit, record_reuse)
├── tests/                    pytest-asyncio test suite
└── website/                  Astro static site on GitHub Pages
```

**Tech stack:** Python 3.11, FastAPI, SQLAlchemy async, pgvector on Supabase, Fly.io, Astro 4, OpenAI gpt-4o-mini + text-embedding-3-small, Tailwind CSS, Resend (email), Fernet (encryption).

---

## Next best steps

### Hygiene / consistency (do first)
- **Consolidate the two hook directories.** `hooks/` (used by `/plugin install`) and `claude_code_integration/hooks/` (used by `install.sh`) have drifted — the top-level version is missing the `record_reuse()` call. Pick one source of truth and have both install paths point to it.
- **Document the `worker_sdk`.** It exists, is async, and could power third-party workers — but there's no doc page or example beyond the in-tree hooks.

### Surface what's already built
- **Wire up versioning in the UI/hooks.** `supersedes_id` validation, the `version` field, and the default-hide-superseded behavior are all in production at the data layer. No UI lets a contributor mark "this supersedes that," and no hook auto-supersedes when the same contributor reruns the same canonical question. A simple heuristic — same handle, same canonical, prior artifact within N days — would activate it immediately.
- **Recency-aware synthesis.** Synthesis currently weights by quality score only. If a canonical has a fresh artifact and an 18-month-old one, both contribute equally. Adding a recency multiplier (or excluding artifacts older than N months from the synthesis) would prevent stale answers from dominating.
- **Staleness detection.** The model has no `is_stale` flag; the only signal is community flags. Auto-marking artifacts stale when the canonical is time-sensitive and `run_date` is older than a configurable threshold would let the UI dim or hide them.

### Discoverability
- **Anonymous full search.** `/search` already returns 5 results to anon users (with summaries hidden), but the search page UI gates the experience behind login. Loosen the JWT requirement on `/search` (with rate limiting) and only redact `synthesized_summary` for anon — most of the wiring is there.
- **Surface contributor profiles in nav.** `/contributor?handle=x` exists; nothing links to it from the leaderboard or artifact cards.

### Bigger bets
- **Quality score in the canonical card.** Show the average artifact quality on canonical browse pages so good content surfaces above stub answers.
- **Multi-language.** Embeddings are language-agnostic, but the sanitizer prompts and synthesizer prompts are English-only.
- **Re-research on staleness.** When a user lands on a canonical whose artifacts are all flagged stale or older than N months, prompt them to rerun — and on submit, link the new artifact via `supersedes_id` automatically.

---

## Contributing

Pull requests welcome. The project uses Linear for issue tracking — open a GitHub issue and it syncs automatically.

Built by [GenAI Gurus](https://genai-gurus.com).
