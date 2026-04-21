#!/usr/bin/env python3
"""
Installs Signal Archive hooks into the Claude Code project settings.
Run from the project root: python claude_code_integration/setup.py
"""
import json
import os
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).parent / "hooks"

def main():
    settings_path = Path(".claude/settings.json")
    settings_path.parent.mkdir(exist_ok=True)

    if settings_path.exists():
        with open(settings_path) as f:
            settings = json.load(f)
    else:
        settings = {}

    pre_hook_cmd = f"python {HOOKS_DIR}/pre_task.py"
    post_hook_cmd = f"python {HOOKS_DIR}/post_task.py"

    settings.setdefault("hooks", {})

    settings["hooks"]["PreToolUse"] = settings["hooks"].get("PreToolUse", [])
    pre_hook_entry = {"matcher": "Task", "hooks": [{"type": "command", "command": pre_hook_cmd}]}
    if pre_hook_entry not in settings["hooks"]["PreToolUse"]:
        settings["hooks"]["PreToolUse"].append(pre_hook_entry)

    settings["hooks"]["PostToolUse"] = settings["hooks"].get("PostToolUse", [])
    post_hook_entry = {"matcher": "Task", "hooks": [{"type": "command", "command": post_hook_cmd}]}
    if post_hook_entry not in settings["hooks"]["PostToolUse"]:
        settings["hooks"]["PostToolUse"].append(post_hook_entry)

    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)

    print(f"Signal Archive hooks installed in {settings_path}")
    print(f"   Pre-task:  {pre_hook_cmd}")
    print(f"   Post-task: {post_hook_cmd}")
    print(f"\nSet these env vars before running Claude Code:")
    print(f"   SIGNAL_ARCHIVE_API_KEY=<your key from POST /contributors>")
    print(f"   SIGNAL_ARCHIVE_API_URL=https://signal-archive-api.fly.dev")
    print(f"   ANTHROPIC_API_KEY=<your key for sanitizer>")

if __name__ == "__main__":
    main()
