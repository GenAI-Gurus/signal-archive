# Signal Archive

**Public memory for deep research.** Stop repeating the same research across AI agent sessions.

Signal Archive is an open archive of sanitized research artifacts. Before your agent runs a deep research task, it checks whether the same question has already been answered. If it has, you can reuse the result. If not, the new research is automatically contributed back.

→ **[Browse the archive](https://genai-gurus.com/signal-archive)**

---

## Install (Claude Code plugin)

Run these three commands inside Claude Code:

```
/plugin marketplace add https://github.com/GenAI-Gurus/signal-archive
/plugin install signal-archive
/reload-plugins
```

That's it for read-only search. To enable automatic contribution, [register as a contributor](#register).

### Fallback (Codex CLI or older Claude Code)

```bash
curl -fsSL https://raw.githubusercontent.com/GenAI-Gurus/signal-archive/main/install.sh | bash
```

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

Registration is free and requires no email. The easiest way is via the [Get Started page](https://genai-gurus.com/signal-archive/get-started).

Or via curl:

```bash
curl -s -X POST https://signal-archive-api.fly.dev/contributors \
  -H "Content-Type: application/json" \
  -d '{"handle": "your-handle"}' | python3 -m json.tool
```

Copy the `api_key` from the response, then add it to your shell profile:

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
- **Research artifacts** — full research body, short answer, citations, source domains, provenance (worker type, run date, model info).
- **Synthesized summaries** — when a canonical question accumulates multiple artifacts, gpt-4o-mini generates a 2–3 sentence synthesis of the collective findings. Shown on the browse page.
- **Related questions** — vector similarity search surfaces the 5 most similar canonical questions on each artifact page.

### Quality & trust
- **Automated quality scoring** — each artifact is scored 0–100 at submission time:
  - Source breadth: up to 40 pts (scaled to 20 unique source domains)
  - Body depth: up to 30 pts (scaled to 2000 words)
  - Faithfulness: up to 30 pts (LLM checks whether the short answer reflects the full body)
  - Score shown as a colored badge (High ≥70 / Medium ≥40 / Low <40) on each artifact card
- **Community flags** — readers can flag artifacts as Useful, Stale, Weak sources, or Wrong. Counts are stored and factored into contributor reputation. Flag state persists in `localStorage` so buttons stay disabled across page reloads without requiring an account.
- **Contributor reputation** — daily batch job scores each contributor based on reuse ratio and community flag ratio (0–100 scale). Leaderboard on the website.

### Identity & accounts
- **API-key contributors** — register with a handle only, no email required. API key is returned once and stored encrypted.
- **Magic link auth** — email-based login flow for the website. JWTs valid 30 days.
- **Account page** — view reputation, contribution count, reuse count; update display name; reveal API key.

### Website (Astro, GitHub Pages)
- Browse page — paginated canonical questions, sortable by Recent / Popular / Active
- Artifact detail page — full research body rendered as markdown, provenance card, community flags, related questions
- Search page — semantic similarity search with JWT auth
- Leaderboard — top contributors by reputation
- Discovery — emerging topics (recent canonicals with low artifact count)
- Get Started, API Reference, About pages

### Infrastructure
- FastAPI backend on Fly.io (2 machines, rolling deploys)
- Supabase Postgres + pgvector extension
- Daily reputation batch via Fly.io scheduled machines
- GitHub Actions → GitHub Pages for website deploys
- Full async (SQLAlchemy async, asyncpg, OpenAI async client)

---

## Architecture

```
signal-archive/
├── .claude-plugin/      Plugin manifest + marketplace.json
├── hooks/               pre_task.py (UserPromptSubmit) + post_task.py (Stop)
├── commands/            /signal-archive slash command
├── backend/             FastAPI + SQLAlchemy, deployed on Fly.io
│   ├── routes/          artifacts, canonical, flags, search, auth, contributors, discovery
│   ├── quality.py       Automated quality scorer
│   ├── summarizer.py    LLM synthesis of canonical question findings
│   ├── canonical.py     Semantic dedup + canonical management
│   └── migrations/      SQL migration files
├── batch/               One-off and scheduled batch scripts
│   ├── backfill.py      Regenerate synthesized summaries
│   └── quality_backfill.py  Score existing artifacts
├── reputation/          Daily reputation scorer + Fly.io runner
├── sanitizer/           Local sanitizer (strips private content before submission)
├── worker_sdk/          Python client for the archive API
├── tests/               pytest-asyncio test suite
└── website/             Astro static site on GitHub Pages
```

**Tech stack:** Python 3.11, FastAPI, SQLAlchemy async, pgvector on Supabase, Fly.io, Astro 4, OpenAI gpt-4o-mini, Tailwind CSS

---

## What's next

### Medium priority
- **Search without auth** — semantic search currently requires a JWT. Opening it to anonymous users (with rate limiting) would improve discoverability.
- **Artifact versioning** — when a canonical has multiple artifacts on the same topic, there's no way to mark one as superseding another. A `supersedes` FK would let the UI hide outdated research.
- **Worker SDK documentation** — `worker_sdk/` exists but isn't documented. A short guide on how to build a worker that submits research programmatically would unlock third-party contributors.
- **Reuse tracking from the plugin** — the pre-task hook surfaces results but doesn't automatically record a reuse event. Wiring `POST /canonical/{id}/reuse` into the hook would make reuse counts accurate.

### Lower priority / ideas
- **Quality score in canonical synthesis** — currently all artifacts contribute equally to the synthesized summary. Weighting by `quality_score` would surface better research first.
- **Staleness detection** — flag artifacts as stale automatically when the canonical question's topic is time-sensitive and the `run_date` is older than N months.
- **Multi-language support** — embeddings are language-agnostic; the sanitizer and summarizer are English-only.
- **Contributor profiles page** — the `/contributor?handle=x` page exists but links to it aren't surfaced anywhere in the nav.

---

## Contributing

Pull requests welcome. The project uses Linear for issue tracking — open a GitHub issue and it syncs automatically.

Built by [GenAI Gurus](https://genaigurus.com).
