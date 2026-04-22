import shutil

def detect_cli() -> str:
    for cli in ("claude", "codex"):
        if shutil.which(cli):
            return cli
    raise EnvironmentError(
        "Neither 'claude' nor 'codex' CLI found in PATH. "
        "Install Claude Code (claude.ai/code) or Codex to use Signal Archive hooks."
    )
