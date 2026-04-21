# signal-archive

Public agent-first archive of deep research artifacts

---

## Tech Stack

- **Language:** Python

---

## Secrets

Never hardcode secrets. Fetch at runtime via 1Password CLI:

```bash
op read "op://ch-os/<item-name>/<field>"        # non-sensitive (e.g. deploy key)
op read "op://ch-os-priv/<item-name>/<field>"   # sensitive (e.g. API keys)
```

For MCP servers, use `op run` to inject env vars automatically.

---

## Linear

All tasks, todos, and next steps go in **Linear** — not in READMEs or code comments.

- Workspace: CH-OS (carloshvp@gmail.com)
- Project: `signal-archive` (ID: `89d97787-5c7d-49a6-b372-e00dc82cdd50`)
- API key: `op read "op://ch-os-priv/Linear API key ch-os-admin/credential"`

---

## GitHub

- Repo: `carloshvp/signal-archive` (private)
- Remote: `git@github-signal-archive:carloshvp/signal-archive.git`
- Auth: deploy key via SSH alias `github-signal-archive` in `~/.ssh/config`
- Deploy key: `op://ch-os/main-mac → github/signal-archive (deploy key)/Keys/private_key`

---

## Commit and Push

After every significant change, commit and push immediately — no confirmation needed.

- Concise commit messages describing what changed and why
- Pull (rebase) before pushing if working across sessions
- Do not batch unrelated changes into one commit
