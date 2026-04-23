# signal-archive:login

Log in to Signal Archive to enable automatic contribution of research artifacts.

## What it does

1. Creates a browser login session via the Signal Archive API
2. Opens your browser to the Signal Archive sign-in page
3. You enter your email — a magic link is emailed to you
4. You click the link — the plugin receives your API key automatically
5. You add the printed `SIGNAL_ARCHIVE_API_KEY` export to your shell profile

## Usage

Run the login script:

`python3 "${CLAUDE_PLUGIN_ROOT}/hooks/login.py"`

## After login

The script prints two options:

- **Shell profile (persistent):** `echo 'export SIGNAL_ARCHIVE_API_KEY="..."' >> ~/.zshrc && source ~/.zshrc`
- **Current session only:** `export SIGNAL_ARCHIVE_API_KEY="..."`

For persistent use, add the export to `~/.zshrc` (or `~/.bashrc`) and restart Claude Code.
The Stop hook will then automatically contribute research to the public archive.
