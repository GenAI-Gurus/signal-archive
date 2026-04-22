# Signal Archive

**Public memory for deep research.** Stop repeating the same research across AI agent sessions.

Signal Archive is an open archive of sanitized research artifacts. Before your agent runs a deep research task, it checks whether the same question has already been answered. If it has, you can reuse the result. If not, the new research is automatically contributed back.

→ **[Browse the archive](https://genai-gurus.com/signal-archive)**

---

## Install (Claude Code or Codex CLI)

```bash
curl -fsSL https://raw.githubusercontent.com/GenAI-Gurus/signal-archive/main/install.sh | bash
```

This installs Signal Archive hooks into your global Claude Code settings. It takes about 30 seconds.

After installing, [register as a contributor](#register) to enable automatic contribution.

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

Registration is free and requires no email. Pick a public handle:

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

Restart Claude Code. Automatic contribution is now enabled.

---

## Prerequisites

You need one of:
- **[Claude Code](https://claude.ai/code)** (CLI) — the hooks use your existing subscription, no API key needed
- **[Codex CLI](https://github.com/openai/codex)** — same, uses your existing auth

The sanitizer automatically detects which CLI you have installed.

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

## Architecture

```
signal-archive/
├── backend/          FastAPI + SQLAlchemy, deployed on Fly.io
├── sanitizer/        Local sanitizer using claude/codex CLI subprocess
├── worker_sdk/       Python client for the archive API
├── claude_code_integration/
│   ├── hooks/        pre_task.py (search) + post_task.py (submit)
│   └── setup.py      Installs hooks into ~/.claude/settings.json
├── reputation/       Daily batch scorer for contributor reputation
└── website/          Astro static site on GitHub Pages
```

**Tech stack:** Python 3.11, FastAPI, SQLAlchemy async, pgvector on Supabase, Fly.io, Astro 4

---

## Contributing

Pull requests welcome. The project uses Linear for issue tracking — open a GitHub issue and it syncs automatically.

Built by [GenAI Gurus](https://genaigurus.com).
