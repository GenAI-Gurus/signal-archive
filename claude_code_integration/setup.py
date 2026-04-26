#!/usr/bin/env python3
"""
Installs Signal Archive hooks into Claude Code settings.

Usage:
  python setup.py           # installs into current project (.claude/settings.json)
  python setup.py --global  # installs globally (~/.claude/settings.json)
"""
import json
import sys
from pathlib import Path

HOOKS_DIR = (Path(__file__).parent.parent / "hooks").resolve()
PRE_HOOK_CMD = f"python3 {HOOKS_DIR}/pre_task.py"
POST_HOOK_CMD = f"python3 {HOOKS_DIR}/post_task.py"

def install(global_install: bool = False):
    if global_install:
        settings_path = Path.home() / ".claude" / "settings.json"
    else:
        settings_path = Path(".claude") / "settings.json"

    settings_path.parent.mkdir(parents=True, exist_ok=True)

    if settings_path.exists():
        with open(settings_path) as f:
            settings = json.load(f)
    else:
        settings = {}

    settings.setdefault("hooks", {})

    # UserPromptSubmit: search archive before every research task
    settings["hooks"].setdefault("UserPromptSubmit", [])
    pre_entry = {"hooks": [{"type": "command", "command": PRE_HOOK_CMD}]}
    if pre_entry not in settings["hooks"]["UserPromptSubmit"]:
        settings["hooks"]["UserPromptSubmit"].append(pre_entry)

    # Stop: contribute artifact after task completes (only if SIGNAL_ARCHIVE_API_KEY is set)
    settings["hooks"].setdefault("Stop", [])
    post_entry = {"hooks": [{"type": "command", "command": POST_HOOK_CMD}]}
    if post_entry not in settings["hooks"]["Stop"]:
        settings["hooks"]["Stop"].append(post_entry)

    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)

    scope = "globally" if global_install else f"in {settings_path}"
    print(f"\n✓ Signal Archive hooks installed {scope}")
    print(f"  Pre-task search:  {PRE_HOOK_CMD}")
    print(f"  Post-task submit: {POST_HOOK_CMD}")
    print("""
Next steps:
  1. Register as a contributor:
     curl -X POST https://signal-archive-api.fly.dev/contributors \\
       -H "Content-Type: application/json" \\
       -d '{"handle": "your-handle"}'

  2. Add your API key to your shell profile (~/.zshrc or ~/.bashrc):
     export SIGNAL_ARCHIVE_API_KEY="key-from-step-1"

  3. Restart Claude Code — done!
""")


if __name__ == "__main__":
    install(global_install="--global" in sys.argv)
