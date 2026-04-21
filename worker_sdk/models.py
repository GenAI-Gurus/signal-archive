from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Citation:
    url: str
    title: str
    domain: str

@dataclass
class SearchMatch:
    canonical_question_id: str
    title: str
    synthesized_summary: Optional[str]
    similarity: float
    artifact_count: int
    reuse_count: int
    last_updated_at: str

@dataclass
class ArtifactPayload:
    cleaned_question: str
    cleaned_prompt: str
    short_answer: str
    full_body: str
    citations: list[Citation]
    run_date: datetime
    worker_type: str
    source_domains: list[str]
    prompt_modified: bool
    clarifying_qa: list[dict] = field(default_factory=list)
    model_info: Optional[str] = None
    version: Optional[str] = None
