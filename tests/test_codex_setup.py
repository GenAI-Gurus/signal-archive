import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pathlib import Path
from unittest.mock import patch
import codex_integration.setup as setup_mod


def _run_install(tmp_home: Path):
    """Run codex_integration.setup.install() with home dir patched to tmp_home."""
    with patch.object(Path, "home", return_value=tmp_home):
        setup_mod.install()


def test_creates_codex_instructions_file_when_missing(tmp_path):
    _run_install(tmp_path)
    instructions = tmp_path / ".codex" / "instructions.md"
    assert instructions.exists()
    content = instructions.read_text()
    assert "Signal Archive" in content
    assert "pre_task.py" in content
    assert "post_task.py" in content


def test_appends_to_existing_instructions_file(tmp_path):
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()
    instructions = codex_dir / "instructions.md"
    instructions.write_text("# My existing Codex instructions\n\nAlways use TypeScript.\n")
    _run_install(tmp_path)
    content = instructions.read_text()
    assert "My existing Codex instructions" in content
    assert "Signal Archive" in content


def test_install_is_idempotent(tmp_path):
    _run_install(tmp_path)
    _run_install(tmp_path)
    instructions = tmp_path / ".codex" / "instructions.md"
    content = instructions.read_text()
    # Guard block should appear exactly once
    assert content.count("<!-- Signal Archive Integration") == 1


def test_creates_codex_directory_if_missing(tmp_path):
    codex_dir = tmp_path / ".codex"
    assert not codex_dir.exists()
    _run_install(tmp_path)
    assert codex_dir.exists()
