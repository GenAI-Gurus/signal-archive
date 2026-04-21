from dataclasses import dataclass, field

@dataclass
class SanitizationResult:
    cleaned_prompt: str
    was_modified: bool
    removed_categories: list[str]
    safe_to_submit: bool
    reason: str = ""
