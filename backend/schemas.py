from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

class CitationItem(BaseModel):
    url: str
    title: str
    domain: str

class ClarifyingQA(BaseModel):
    question: str
    answer: str

class ArtifactSubmit(BaseModel):
    model_config = {"protected_namespaces": ()}

    cleaned_question: str
    cleaned_prompt: str
    clarifying_qa: list[ClarifyingQA] = []
    short_answer: str
    full_body: str
    citations: list[CitationItem]
    run_date: datetime
    worker_type: str
    model_info: Optional[str] = None
    source_domains: list[str] = []
    prompt_modified: bool = False
    version: Optional[str] = None

class ArtifactResponse(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: UUID
    canonical_question_id: Optional[UUID] = None
    contributor_handle: Optional[str] = None
    cleaned_question: str
    short_answer: str
    full_body: str
    citations: list[CitationItem]
    run_date: datetime
    worker_type: str
    model_info: Optional[str] = None
    source_domains: list[str]
    prompt_modified: bool
    useful_count: int
    stale_count: int
    weakly_sourced_count: int
    wrong_count: int
    created_at: datetime

class CanonicalQuestionResponse(BaseModel):
    id: UUID
    title: str
    synthesized_summary: Optional[str] = None
    artifact_count: int
    reuse_count: int
    created_at: datetime
    last_updated_at: datetime

    model_config = {"from_attributes": True}

class SearchResult(BaseModel):
    canonical_question_id: UUID
    title: str
    synthesized_summary: Optional[str] = None
    similarity: float
    artifact_count: int
    reuse_count: int
    last_updated_at: datetime

class ContributorResponse(BaseModel):
    handle: str
    display_name: Optional[str] = None
    total_contributions: int
    total_reuse_count: int
    reputation_score: float
    created_at: datetime

    model_config = {"from_attributes": True}

class ContributorCreate(BaseModel):
    handle: str
    display_name: Optional[str] = None

class ContributorCreated(BaseModel):
    handle: str
    api_key: str

class FlagCreate(BaseModel):
    artifact_id: UUID
    flag_type: Literal["useful", "stale", "weakly_sourced", "wrong"]

class MagicLinkRequest(BaseModel):
    email: EmailStr
    cli_session_id: Optional[str] = None

class MagicLinkVerify(BaseModel):
    token: str
    handle: Optional[str] = None
    display_name: Optional[str] = None

class AuthResponse(BaseModel):
    jwt: str
    handle: str
    email: str
    is_new: bool
    api_key: str

class CliSessionResponse(BaseModel):
    session_id: str
    login_url: str

class CliSessionPoll(BaseModel):
    ready: bool
    api_key: Optional[str] = None

class TokenRequest(BaseModel):
    api_key: str = Field(min_length=1)

class TokenResponse(BaseModel):
    jwt: str
    handle: str
    email: str

class MeResponse(BaseModel):
    handle: str
    display_name: Optional[str] = None
    email: str
    total_contributions: int
    total_reuse_count: int
    reputation_score: float
    created_at: datetime

    model_config = {"from_attributes": True}

class MePatch(BaseModel):
    display_name: Optional[str] = None

class ApiKeyResponse(BaseModel):
    api_key: str
