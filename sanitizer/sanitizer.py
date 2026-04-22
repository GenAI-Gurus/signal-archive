import json
import subprocess
from .client import detect_cli
from .prompt import SYSTEM_PROMPT
from .models import SanitizationResult

def sanitize_prompt(prompt: str) -> SanitizationResult:
    cli = detect_cli()
    full_prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Sanitize the following research prompt and return only the JSON:\n\n"
        f"{prompt}"
    )
    result = subprocess.run(
        [cli, "-p", full_prompt],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{cli} CLI error: {result.stderr.strip()}")

    raw = result.stdout.strip()
    # Strip markdown code fences if the model wrapped the JSON
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        raw = raw.rsplit("```", 1)[0].strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse sanitizer response: {e}\nRaw: {raw}") from e

    return SanitizationResult(
        cleaned_prompt=data["cleaned_prompt"],
        was_modified=data["was_modified"],
        removed_categories=data.get("removed_categories", []),
        safe_to_submit=data["safe_to_submit"],
        reason=data.get("reason", ""),
    )
