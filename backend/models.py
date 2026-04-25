import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from database import Base

class Contributor(Base):
    __tablename__ = "contributors"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    handle = Column(String, unique=True, nullable=False)
    display_name = Column(String)
    api_key_hash = Column(String, nullable=False)
    total_contributions = Column(Integer, default=0)
    total_reuse_count = Column(Integer, default=0)
    reputation_score = Column(Float, default=0.0)
    email = Column(String, unique=True, nullable=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    api_key_enc = Column(Text, nullable=True)  # Fernet-encrypted copy of api_key
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class CanonicalQuestion(Base):
    __tablename__ = "canonical_questions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    synthesized_summary = Column(Text)
    embedding = Column(Vector(1536))
    artifact_count = Column(Integer, default=0)
    reuse_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ResearchArtifact(Base):
    __tablename__ = "research_artifacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_question_id = Column(UUID(as_uuid=True), ForeignKey("canonical_questions.id"), nullable=True)
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("contributors.id"), nullable=True)
    cleaned_question = Column(Text, nullable=False)
    cleaned_prompt = Column(Text, nullable=False)
    clarifying_qa = Column(JSONB, default=list)
    short_answer = Column(Text, nullable=False)
    full_body = Column(Text, nullable=False)
    citations = Column(JSONB, nullable=False, default=list)
    run_date = Column(DateTime(timezone=True), nullable=False)
    worker_type = Column(String, nullable=False)
    model_info = Column(String)
    source_domains = Column(ARRAY(Text), default=list)
    prompt_modified = Column(Boolean, default=False)
    version = Column(String)
    embedding = Column(Vector(1536))
    useful_count = Column(Integer, default=0)
    stale_count = Column(Integer, default=0)
    weakly_sourced_count = Column(Integer, default=0)
    wrong_count = Column(Integer, default=0)
    supersedes_id = Column(UUID(as_uuid=True), ForeignKey("research_artifacts.id"), nullable=True)
    quality_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class CommunityFlag(Base):
    __tablename__ = "community_flags"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id = Column(UUID(as_uuid=True), ForeignKey("research_artifacts.id"), nullable=False)
    flag_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ReuseEvent(Base):
    __tablename__ = "reuse_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_question_id = Column(UUID(as_uuid=True), ForeignKey("canonical_questions.id"), nullable=False)
    artifact_id = Column(UUID(as_uuid=True), ForeignKey("research_artifacts.id"), nullable=True)
    reused_by = Column(String)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class MagicLinkToken(Base):
    __tablename__ = "magic_link_tokens"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    cli_session_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class CliSession(Base):
    __tablename__ = "cli_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    claimed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
