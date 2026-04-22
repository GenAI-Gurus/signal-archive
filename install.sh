#!/usr/bin/env bash
set -euo pipefail

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

# Install Python dependency (httpx for API calls)
echo "→ Installing dependencies"
python3 -m pip install --quiet --upgrade httpx

# Install Claude Code hooks globally
echo "→ Installing Claude Code hooks"
python3 "$INSTALL_DIR/claude_code_integration/setup.py" --global

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Signal Archive is installed. To start contributing:"
echo ""
echo "  1. Register (free, no email required):"
echo ""
echo '     curl -s -X POST https://signal-archive-api.fly.dev/contributors \'
echo '       -H "Content-Type: application/json" \'
echo '       -d '"'"'{"handle": "YOUR_HANDLE"}'"'"' | python3 -m json.tool'
echo ""
echo "  2. Copy your api_key from the output above, then:"
echo ""
echo '     echo '"'"'export SIGNAL_ARCHIVE_API_KEY="your-key-here"'"'"' >> ~/.zshrc'
echo '     source ~/.zshrc'
echo ""
echo "  3. Restart Claude Code — that's it."
echo ""
echo "Archive: https://genai-gurus.com/signal-archive"
echo "GitHub:  https://github.com/GenAI-Gurus/signal-archive"
echo ""
