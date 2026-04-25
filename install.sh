#!/usr/bin/env bash
set -euo pipefail

# Signal Archive — install via Claude Code plugin (recommended)
#
# The preferred way to install is the Claude Code plugin:
#
#   /plugin marketplace add https://github.com/GenAI-Gurus/signal-archive
#   /plugin install signal-archive
#
# This script is a fallback for environments without the /plugin command
# (e.g. Codex CLI, older Claude Code versions).

INSTALL_DIR="$HOME/.signal-archive"
REPO_URL="https://github.com/GenAI-Gurus/signal-archive.git"

echo ""
echo "Installing Signal Archive integration..."
echo ""

# Clone or update
if [ -d "$INSTALL_DIR/.git" ]; then
  echo "→ Updating existing install at $INSTALL_DIR"
  git -C "$INSTALL_DIR" pull --rebase --quiet
else
  echo "→ Cloning to $INSTALL_DIR"
  git clone --depth 1 --quiet "$REPO_URL" "$INSTALL_DIR"
fi

# Install Python dependency
echo "→ Installing dependencies"
python3 -m pip install --quiet --upgrade httpx

# Claude Code integration
if command -v claude &>/dev/null; then
  echo "→ Installing Claude Code hooks"
  python3 "$INSTALL_DIR/claude_code_integration/setup.py" --global
else
  echo "→ Claude Code not found — skipping Claude Code hooks"
fi

# Codex CLI integration
if command -v codex &>/dev/null; then
  echo "→ Installing Codex CLI integration"
  python3 "$INSTALL_DIR/codex_integration/setup.py"
else
  echo "→ Codex CLI not found — skipping Codex integration"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Signal Archive is installed. To start contributing:"
echo ""
echo "  1. Register at https://genai-gurus.com/signal-archive/get-started"
echo "     (or via curl):"
echo ""
echo '     curl -s -X POST https://signal-archive-api.fly.dev/contributors \'
echo '       -H "Content-Type: application/json" \'
echo '       -d '"'"'{"handle": "YOUR_HANDLE"}'"'"' | python3 -m json.tool'
echo ""
echo "  2. Add your api_key to your shell profile:"
echo ""
echo '     echo '"'"'export SIGNAL_ARCHIVE_API_KEY="your-key-here"'"'"' >> ~/.zshrc'
echo '     source ~/.zshrc'
echo ""
echo "  3. Restart Claude Code or Codex — that's it."
echo ""
echo "Archive: https://genai-gurus.com/signal-archive"
echo "GitHub:  https://github.com/GenAI-Gurus/signal-archive"
echo ""
