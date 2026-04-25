#!/usr/bin/env python3
"""
Installs Signal Archive integration into ~/.codex/instructions.md.

Usage:
  python3 setup.py
"""
from pathlib import Path

TEMPLATE_PATH = Path(__file__).parent / "instructions_template.md"
HOOKS_DIR = (Path(__file__).parent / "hooks").resolve()
GUARD_START = "<!-- Signal Archive Integration"
GUARD_END = "<!-- End Signal Archive Integration -->"


def install():
    template = TEMPLATE_PATH.read_text()

    codex_dir = Path.home() / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)
    instructions_path = codex_dir / "instructions.md"

    if instructions_path.exists():
        existing = instructions_path.read_text()
        if GUARD_START in existing:
            print("✓ Signal Archive integration already installed in ~/.codex/instructions.md")
            return
        updated = existing.rstrip() + "\n\n" + template
    else:
        updated = template

    instructions_path.write_text(updated)
    print(f"✓ Signal Archive integration installed in {instructions_path}")
    print(f"  Pre-task search:  python3 {HOOKS_DIR}/pre_task.py")
    print(f"  Post-task submit: python3 {HOOKS_DIR}/post_task.py")
    print("""
Next steps:
  1. Register as a contributor:
     curl -X POST https://signal-archive-api.fly.dev/contributors \\
       -H "Content-Type: application/json" \\
       -d '{"handle": "your-handle"}'

  2. Add your API key to your shell profile (~/.zshrc or ~/.bashrc):
     export SIGNAL_ARCHIVE_API_KEY="key-from-step-1"

  3. Restart Codex — that's it.
""")


if __name__ == "__main__":
    install()
