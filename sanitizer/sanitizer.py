import json
from .client import get_client
from .prompt import SYSTEM_PROMPT
from .models import SanitizationResult

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

def sanitize_prompt(prompt: str) -> SanitizationResult:
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text
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
