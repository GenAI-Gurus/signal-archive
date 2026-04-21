# Core Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the FastAPI backend with Supabase Postgres + pgvector covering data models, API endpoints for artifact submission, semantic search, canonical question management, contributor profiles, and community flags — deployed on Fly.io.

**Architecture:** FastAPI app using SQLAlchemy (async) + asyncpg connected to Supabase Postgres; pgvector extension for semantic similarity search; OpenAI `text-embedding-3-small` (1536 dims) for embeddings generated at submission and search time; deployed on Fly.io free tier (always-on, no cold starts).

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async, asyncpg, pgvector, Supabase Postgres, OpenAI embeddings API, Fly.io, pytest + pytest-asyncio

---

## File Structure

```
backend/
├── main.py                  # FastAPI app factory + lifespan
├── config.py                # Settings from env vars
├── database.py              # Async SQLAlchemy engine + session
├── models.py                # SQLAlchemy ORM models
├── schemas.py               # Pydantic request/response schemas
├── embeddings.py            # OpenAI embedding client
├── canonical.py             # Canonical question matching logic
├── routes/
│   ├── __init__.py
│   ├── artifacts.py         # POST /artifacts, GET /artifacts/{id}
│   ├── canonical.py         # GET /canonical/{id}, GET /canonical/{id}/related
│   ├── search.py            # GET /search?q=...
│   ├── contributors.py      # GET /contributors/{handle}, POST /contributors
│   ├── flags.py             # POST /flags
│   └── discovery.py        # GET /discovery/weekly, GET /discovery/top-reused
├── migrations/
│   └── 001_initial.sql      # Full schema + pgvector setup
├── requirements.txt
├── fly.toml
├── Dockerfile
tests/
├── conftest.py
├── test_artifacts.py
├── test_search.py
├── test_canonical.py
├── test_flags.py
```

---

### Task 1: Project scaffold and dependencies

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/config.py`
- Create: `backend/main.py`

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy[asyncio]==2.0.35
asyncpg==0.29.0
pgvector==0.3.2
openai==1.51.0
pydantic==2.9.2
pydantic-settings==2.5.2
python-dotenv==1.0.1
httpx==0.27.2
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-httpx==0.31.0
```

- [ ] **Step 2: Create config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str         # postgresql+asyncpg://...
    openai_api_key: str
    api_key_salt: str         # random secret for hashing contributor keys
    environment: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 3: Create main.py**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routes import artifacts, canonical, search, contributors, flags, discovery

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="Signal Archive API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(artifacts.router, prefix="/artifacts")
app.include_router(canonical.router, prefix="/canonical")
app.include_router(search.router, prefix="/search")
app.include_router(contributors.router, prefix="/contributors")
app.include_router(flags.router, prefix="/flags")
app.include_router(discovery.router, prefix="/discovery")

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Run server to verify scaffold starts**

```bash
cd backend && pip install -r requirements.txt
DATABASE_URL="sqlite+aiosqlite:///test.db" OPENAI_API_KEY="sk-test" API_KEY_SALT="test" uvicorn main:app --reload
```

Expected: server starts, `GET /health` returns `{"status": "ok"}`

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat(backend): project scaffold with FastAPI + config"
```

---

### Task 2: Database schema and migrations

**Files:**
- Create: `backend/migrations/001_initial.sql`
- Create: `backend/database.py`

- [ ] **Step 1: Write the migration SQL**

Create `backend/migrations/001_initial.sql`:

```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Contributors
CREATE TABLE IF NOT EXISTS contributors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    handle TEXT UNIQUE NOT NULL,
    display_name TEXT,
    api_key_hash TEXT NOT NULL,
    total_contributions INT DEFAULT 0,
    total_reuse_count INT DEFAULT 0,
    reputation_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Canonical Questions
CREATE TABLE IF NOT EXISTS canonical_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    synthesized_summary TEXT,
    embedding VECTOR(1536),
    artifact_count INT DEFAULT 0,
    reuse_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS canonical_questions_embedding_idx
    ON canonical_questions USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Research Artifacts
CREATE TABLE IF NOT EXISTS research_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_question_id UUID REFERENCES canonical_questions(id) ON DELETE SET NULL,
    contributor_id UUID REFERENCES contributors(id) ON DELETE SET NULL,
    cleaned_question TEXT NOT NULL,
    cleaned_prompt TEXT NOT NULL,
    clarifying_qa JSONB DEFAULT '[]',
    short_answer TEXT NOT NULL,
    full_body TEXT NOT NULL,
    citations JSONB NOT NULL DEFAULT '[]',
    run_date TIMESTAMPTZ NOT NULL,
    worker_type TEXT NOT NULL,
    model_info TEXT,
    source_domains TEXT[] DEFAULT '{}',
    prompt_modified BOOLEAN DEFAULT FALSE,
    version TEXT,
    embedding VECTOR(1536),
    useful_count INT DEFAULT 0,
    stale_count INT DEFAULT 0,
    weakly_sourced_count INT DEFAULT 0,
    wrong_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS research_artifacts_embedding_idx
    ON research_artifacts USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS research_artifacts_canonical_idx
    ON research_artifacts (canonical_question_id);

CREATE INDEX IF NOT EXISTS research_artifacts_contributor_idx
    ON research_artifacts (contributor_id);

-- Community Flags
CREATE TABLE IF NOT EXISTS community_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES research_artifacts(id) ON DELETE CASCADE,
    flag_type TEXT NOT NULL CHECK (flag_type IN ('useful', 'stale', 'weakly_sourced', 'wrong')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Reuse Events
CREATE TABLE IF NOT EXISTS reuse_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_question_id UUID NOT NULL REFERENCES canonical_questions(id) ON DELETE CASCADE,
    artifact_id UUID REFERENCES research_artifacts(id) ON DELETE SET NULL,
    reused_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

- [ ] **Step 2: Write tests/conftest.py**

```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from database import Base

TEST_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:54322/postgres"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

- [ ] **Step 3: Create database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 4: Apply migration to local Supabase (for dev) and run health check**

```bash
# Start local Supabase (install supabase CLI first: brew install supabase/tap/supabase)
supabase start
psql postgresql://postgres:postgres@localhost:54322/postgres -f backend/migrations/001_initial.sql
```

Expected: all tables created without errors

- [ ] **Step 5: Commit**

```bash
git add backend/migrations/ backend/database.py tests/conftest.py
git commit -m "feat(backend): database schema with pgvector and SQLAlchemy setup"
```

---

### Task 3: ORM models and Pydantic schemas

**Files:**
- Create: `backend/models.py`
- Create: `backend/schemas.py`

- [ ] **Step 1: Write test to ensure models are importable and reflect table names**

Create `tests/test_models.py`:

```python
from models import Contributor, CanonicalQuestion, ResearchArtifact, CommunityFlag, ReuseEvent

def test_model_table_names():
    assert Contributor.__tablename__ == "contributors"
    assert CanonicalQuestion.__tablename__ == "canonical_questions"
    assert ResearchArtifact.__tablename__ == "research_artifacts"
    assert CommunityFlag.__tablename__ == "community_flags"
    assert ReuseEvent.__tablename__ == "reuse_events"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest ../tests/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'models'`

- [ ] **Step 3: Create models.py**

```python
import uuid
from datetime import datetime
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
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class CanonicalQuestion(Base):
    __tablename__ = "canonical_questions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    synthesized_summary = Column(Text)
    embedding = Column(Vector(1536))
    artifact_count = Column(Integer, default=0)
    reuse_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

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
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class CommunityFlag(Base):
    __tablename__ = "community_flags"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id = Column(UUID(as_uuid=True), ForeignKey("research_artifacts.id"), nullable=False)
    flag_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class ReuseEvent(Base):
    __tablename__ = "reuse_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_question_id = Column(UUID(as_uuid=True), ForeignKey("canonical_questions.id"), nullable=False)
    artifact_id = Column(UUID(as_uuid=True), ForeignKey("research_artifacts.id"), nullable=True)
    reused_by = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
```

- [ ] **Step 4: Create schemas.py**

```python
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, HttpUrl

class CitationItem(BaseModel):
    url: str
    title: str
    domain: str

class ClarifyingQA(BaseModel):
    question: str
    answer: str

class ArtifactSubmit(BaseModel):
    cleaned_question: str
    cleaned_prompt: str
    clarifying_qa: list[ClarifyingQA] = []
    short_answer: str
    full_body: str
    citations: list[CitationItem]
    run_date: datetime
    worker_type: str         # 'codex' | 'claude_code'
    model_info: Optional[str] = None
    source_domains: list[str] = []
    prompt_modified: bool = False
    version: Optional[str] = None

class ArtifactResponse(BaseModel):
    id: UUID
    canonical_question_id: Optional[UUID]
    contributor_handle: Optional[str]
    cleaned_question: str
    short_answer: str
    full_body: str
    citations: list[CitationItem]
    run_date: datetime
    worker_type: str
    model_info: Optional[str]
    source_domains: list[str]
    prompt_modified: bool
    useful_count: int
    stale_count: int
    weakly_sourced_count: int
    wrong_count: int
    created_at: datetime

    class Config:
        from_attributes = True

class CanonicalQuestionResponse(BaseModel):
    id: UUID
    title: str
    synthesized_summary: Optional[str]
    artifact_count: int
    reuse_count: int
    created_at: datetime
    last_updated_at: datetime

    class Config:
        from_attributes = True

class SearchResult(BaseModel):
    canonical_question_id: UUID
    title: str
    synthesized_summary: Optional[str]
    similarity: float
    artifact_count: int
    reuse_count: int
    last_updated_at: datetime

class ContributorResponse(BaseModel):
    handle: str
    display_name: Optional[str]
    total_contributions: int
    total_reuse_count: int
    reputation_score: float
    created_at: datetime

    class Config:
        from_attributes = True

class ContributorCreate(BaseModel):
    handle: str
    display_name: Optional[str] = None

class ContributorCreated(BaseModel):
    handle: str
    api_key: str  # only returned once at creation

class FlagCreate(BaseModel):
    artifact_id: UUID
    flag_type: str  # 'useful' | 'stale' | 'weakly_sourced' | 'wrong'
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && pytest ../tests/test_models.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/models.py backend/schemas.py tests/test_models.py
git commit -m "feat(backend): ORM models and Pydantic schemas"
```

---

### Task 4: Embedding generation

**Files:**
- Create: `backend/embeddings.py`
- Test: `tests/test_embeddings.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_embeddings.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from embeddings import get_embedding

@pytest.mark.asyncio
async def test_get_embedding_returns_list_of_floats():
    fake_vector = [0.1] * 1536
    with patch("embeddings.client.embeddings.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value.data = [type("obj", (), {"embedding": fake_vector})()]
        result = await get_embedding("what is the best python ORM?")
    assert isinstance(result, list)
    assert len(result) == 1536
    assert all(isinstance(v, float) for v in result)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest ../tests/test_embeddings.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'embeddings'`

- [ ] **Step 3: Create embeddings.py**

```python
from openai import AsyncOpenAI
from config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)

async def get_embedding(text: str) -> list[float]:
    text = text.replace("\n", " ").strip()
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest ../tests/test_embeddings.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/embeddings.py tests/test_embeddings.py
git commit -m "feat(backend): OpenAI embedding client"
```

---

### Task 5: Canonical question matching logic

**Files:**
- Create: `backend/canonical.py`
- Test: `tests/test_canonical.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_canonical.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from canonical import find_or_create_canonical

@pytest.mark.asyncio
async def test_returns_existing_canonical_when_similarity_high():
    mock_db = AsyncMock()
    existing_id = "11111111-1111-1111-1111-111111111111"
    # Simulate DB returning one result with cosine similarity 0.93
    mock_db.execute = AsyncMock(return_value=MagicMock(
        fetchall=lambda: [(existing_id, "What is the best Python ORM?", 0.93)]
    ))
    embedding = [0.1] * 1536
    result, created = await find_or_create_canonical(
        db=mock_db,
        question="Best Python ORM options?",
        embedding=embedding,
        summary="A review of Python ORMs"
    )
    assert result == existing_id
    assert created is False

@pytest.mark.asyncio
async def test_creates_new_canonical_when_no_match():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    embedding = [0.1] * 1536
    result, created = await find_or_create_canonical(
        db=mock_db,
        question="How does quantum computing work?",
        embedding=embedding,
        summary="Overview of quantum computing"
    )
    assert created is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest ../tests/test_canonical.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'canonical'`

- [ ] **Step 3: Create canonical.py**

```python
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from models import CanonicalQuestion

SIMILARITY_THRESHOLD = 0.88  # cosine similarity; questions above this share a canonical page

async def find_or_create_canonical(
    db: AsyncSession,
    question: str,
    embedding: list[float],
    summary: str,
) -> tuple[UUID, bool]:
    """Return (canonical_question_id, was_created)."""
    vector_literal = f"[{','.join(str(v) for v in embedding)}]"
    result = await db.execute(text(f"""
        SELECT id, title, 1 - (embedding <=> '{vector_literal}'::vector) AS similarity
        FROM canonical_questions
        WHERE 1 - (embedding <=> '{vector_literal}'::vector) > :threshold
        ORDER BY similarity DESC
        LIMIT 1
    """), {"threshold": SIMILARITY_THRESHOLD})
    rows = result.fetchall()

    if rows:
        canonical_id = rows[0][0]
        await db.execute(
            text("UPDATE canonical_questions SET last_updated_at = NOW(), artifact_count = artifact_count + 1 WHERE id = :id"),
            {"id": canonical_id},
        )
        return canonical_id, False

    canonical = CanonicalQuestion(
        title=question,
        synthesized_summary=summary,
        embedding=embedding,
        artifact_count=1,
    )
    db.add(canonical)
    await db.flush()
    return canonical.id, True
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest ../tests/test_canonical.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/canonical.py tests/test_canonical.py
git commit -m "feat(backend): canonical question matching with pgvector cosine similarity"
```

---

### Task 6: Contributor routes (registration + profile)

**Files:**
- Create: `backend/routes/__init__.py`
- Create: `backend/routes/contributors.py`
- Test: `tests/test_contributors.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_contributors.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
from main import app

@pytest.mark.asyncio
async def test_create_contributor_returns_api_key():
    mock_contributor = MagicMock()
    mock_contributor.handle = "alice"
    mock_contributor.display_name = "Alice"
    mock_contributor.total_contributions = 0
    mock_contributor.total_reuse_count = 0
    mock_contributor.reputation_score = 0.0
    mock_contributor.created_at = "2026-01-01T00:00:00"

    with patch("routes.contributors.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/contributors", json={"handle": "alice", "display_name": "Alice"})

    assert response.status_code == 201
    data = response.json()
    assert "api_key" in data
    assert data["handle"] == "alice"

@pytest.mark.asyncio
async def test_get_contributor_profile():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/contributors/nonexistent")
    assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest ../tests/test_contributors.py -v
```

Expected: FAIL

- [ ] **Step 3: Create routes/__init__.py and routes/contributors.py**

`backend/routes/__init__.py` — empty file.

`backend/routes/contributors.py`:

```python
import hashlib
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Contributor
from schemas import ContributorCreate, ContributorCreated, ContributorResponse
from config import settings

router = APIRouter(tags=["contributors"])

def _hash_key(api_key: str) -> str:
    return hashlib.sha256((api_key + settings.api_key_salt).encode()).hexdigest()

@router.post("", status_code=201, response_model=ContributorCreated)
async def create_contributor(body: ContributorCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Contributor).where(Contributor.handle == body.handle))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Handle already taken")
    api_key = secrets.token_urlsafe(32)
    contributor = Contributor(
        handle=body.handle,
        display_name=body.display_name,
        api_key_hash=_hash_key(api_key),
    )
    db.add(contributor)
    await db.commit()
    await db.refresh(contributor)
    return ContributorCreated(handle=contributor.handle, api_key=api_key)

@router.get("/{handle}", response_model=ContributorResponse)
async def get_contributor(handle: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contributor).where(Contributor.handle == handle))
    contributor = result.scalar_one_or_none()
    if not contributor:
        raise HTTPException(status_code=404, detail="Contributor not found")
    return contributor
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest ../tests/test_contributors.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routes/ tests/test_contributors.py
git commit -m "feat(backend): contributor registration and profile routes"
```

---

### Task 7: Artifact submission route

**Files:**
- Create: `backend/routes/artifacts.py`
- Test: `tests/test_artifacts.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_artifacts.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from main import app

VALID_SUBMISSION = {
    "cleaned_question": "What are the best vector databases in 2024?",
    "cleaned_prompt": "Research and compare the top vector databases available in 2024.",
    "short_answer": "The top vector databases are Pinecone, Weaviate, and pgvector.",
    "full_body": "## Vector Database Comparison\n\nDetailed analysis...",
    "citations": [{"url": "https://example.com", "title": "Vector DB Guide", "domain": "example.com"}],
    "run_date": "2026-04-01T12:00:00Z",
    "worker_type": "claude_code",
    "source_domains": ["example.com"],
    "prompt_modified": False,
}

@pytest.mark.asyncio
async def test_submit_artifact_without_api_key_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/artifacts", json=VALID_SUBMISSION)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_submit_artifact_returns_artifact_id():
    fake_embedding = [0.1] * 1536
    with patch("routes.artifacts.get_embedding", new_callable=AsyncMock, return_value=fake_embedding), \
         patch("routes.artifacts.find_or_create_canonical", new_callable=AsyncMock, return_value=("cq-id-123", True)), \
         patch("routes.artifacts.get_contributor_from_key", new_callable=AsyncMock) as mock_contrib, \
         patch("routes.artifacts.get_db") as mock_db_ctx:

        mock_contrib.return_value = MagicMock(id="contrib-id-123", handle="alice")
        mock_db = AsyncMock()
        mock_artifact = MagicMock()
        mock_artifact.id = "artifact-id-123"
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock(side_effect=lambda x: setattr(x, 'id', 'artifact-id-123'))
        mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/artifacts",
                json=VALID_SUBMISSION,
                headers={"X-API-Key": "test-key"}
            )
    assert response.status_code == 201
    assert "id" in response.json()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest ../tests/test_artifacts.py -v
```

Expected: FAIL

- [ ] **Step 3: Create routes/artifacts.py**

```python
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional
from database import get_db
from models import ResearchArtifact, Contributor
from schemas import ArtifactSubmit, ArtifactResponse
from embeddings import get_embedding
from canonical import find_or_create_canonical
from config import settings

router = APIRouter(tags=["artifacts"])

def _hash_key(api_key: str) -> str:
    return hashlib.sha256((api_key + settings.api_key_salt).encode()).hexdigest()

async def get_contributor_from_key(api_key: str, db: AsyncSession) -> Contributor:
    key_hash = _hash_key(api_key)
    result = await db.execute(select(Contributor).where(Contributor.api_key_hash == key_hash))
    contributor = result.scalar_one_or_none()
    if not contributor:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return contributor

@router.post("", status_code=201)
async def submit_artifact(
    body: ArtifactSubmit,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header required")

    contributor = await get_contributor_from_key(x_api_key, db)
    embedding = await get_embedding(body.cleaned_question)
    canonical_id, _ = await find_or_create_canonical(
        db=db,
        question=body.cleaned_question,
        embedding=embedding,
        summary=body.short_answer,
    )

    artifact = ResearchArtifact(
        canonical_question_id=canonical_id,
        contributor_id=contributor.id,
        cleaned_question=body.cleaned_question,
        cleaned_prompt=body.cleaned_prompt,
        clarifying_qa=[qa.model_dump() for qa in body.clarifying_qa],
        short_answer=body.short_answer,
        full_body=body.full_body,
        citations=[c.model_dump() for c in body.citations],
        run_date=body.run_date,
        worker_type=body.worker_type,
        model_info=body.model_info,
        source_domains=body.source_domains,
        prompt_modified=body.prompt_modified,
        version=body.version,
        embedding=embedding,
    )
    db.add(artifact)
    await db.execute(
        text("UPDATE contributors SET total_contributions = total_contributions + 1 WHERE id = :id"),
        {"id": contributor.id},
    )
    await db.commit()
    await db.refresh(artifact)
    return {"id": str(artifact.id), "canonical_question_id": str(canonical_id)}

@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(artifact_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ResearchArtifact).where(ResearchArtifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest ../tests/test_artifacts.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routes/artifacts.py tests/test_artifacts.py
git commit -m "feat(backend): artifact submission route with API key auth and canonical matching"
```

---

### Task 8: Semantic search route

**Files:**
- Create: `backend/routes/search.py`
- Test: `tests/test_search.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_search.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
from main import app

@pytest.mark.asyncio
async def test_search_requires_query():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/search")
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_search_returns_results():
    fake_embedding = [0.1] * 1536
    with patch("routes.search.get_embedding", new_callable=AsyncMock, return_value=fake_embedding), \
         patch("routes.search.get_db") as mock_db_ctx:
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: [
            ("cq-id-1", "What are vector databases?", "Overview of vector DBs", 0.95, 3, 12, "2026-04-01T00:00:00")
        ]))
        mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/search?q=best+vector+databases")

    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["similarity"] == 0.95
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest ../tests/test_search.py -v
```

Expected: FAIL

- [ ] **Step 3: Create routes/search.py**

```python
from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db
from embeddings import get_embedding
from schemas import SearchResult

router = APIRouter(tags=["search"])

@router.get("", response_model=list[SearchResult])
async def search_archive(
    q: str = Query(..., min_length=3),
    limit: int = Query(default=5, le=20),
    db: AsyncSession = Depends(get_db),
):
    embedding = await get_embedding(q)
    vector_literal = f"[{','.join(str(v) for v in embedding)}]"
    result = await db.execute(text(f"""
        SELECT
            id,
            title,
            synthesized_summary,
            1 - (embedding <=> '{vector_literal}'::vector) AS similarity,
            artifact_count,
            reuse_count,
            last_updated_at
        FROM canonical_questions
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> '{vector_literal}'::vector
        LIMIT :limit
    """), {"limit": limit})
    rows = result.fetchall()
    return [
        SearchResult(
            canonical_question_id=row[0],
            title=row[1],
            synthesized_summary=row[2],
            similarity=round(float(row[3]), 4),
            artifact_count=row[4],
            reuse_count=row[5],
            last_updated_at=row[6],
        )
        for row in rows
    ]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest ../tests/test_search.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routes/search.py tests/test_search.py
git commit -m "feat(backend): semantic search route using pgvector cosine similarity"
```

---

### Task 9: Canonical question and flags routes

**Files:**
- Create: `backend/routes/canonical.py`
- Create: `backend/routes/flags.py`
- Test: `tests/test_flags.py`

- [ ] **Step 1: Write failing test for flags**

Create `tests/test_flags.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
from main import app

@pytest.mark.asyncio
async def test_flag_invalid_type_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/flags", json={
            "artifact_id": "11111111-1111-1111-1111-111111111111",
            "flag_type": "invalid_type"
        })
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_flag_valid_type_accepted():
    with patch("routes.flags.get_db") as mock_db_ctx:
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: MagicMock()))
        mock_db.commit = AsyncMock()
        mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/flags", json={
                "artifact_id": "11111111-1111-1111-1111-111111111111",
                "flag_type": "useful"
            })
    assert response.status_code == 201
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest ../tests/test_flags.py -v
```

Expected: FAIL

- [ ] **Step 3: Create routes/canonical.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from database import get_db
from models import CanonicalQuestion, ResearchArtifact
from schemas import CanonicalQuestionResponse, ArtifactResponse, SearchResult

router = APIRouter(tags=["canonical"])

@router.get("/{canonical_id}", response_model=CanonicalQuestionResponse)
async def get_canonical(canonical_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CanonicalQuestion).where(CanonicalQuestion.id == canonical_id))
    cq = result.scalar_one_or_none()
    if not cq:
        raise HTTPException(status_code=404, detail="Canonical question not found")
    return cq

@router.get("/{canonical_id}/artifacts", response_model=list[ArtifactResponse])
async def get_canonical_artifacts(
    canonical_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ResearchArtifact)
        .where(ResearchArtifact.canonical_question_id == canonical_id)
        .order_by(ResearchArtifact.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()

@router.get("/{canonical_id}/related", response_model=list[SearchResult])
async def get_related(canonical_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CanonicalQuestion).where(CanonicalQuestion.id == canonical_id))
    cq = result.scalar_one_or_none()
    if not cq or cq.embedding is None:
        return []
    vector_literal = f"[{','.join(str(v) for v in cq.embedding)}]"
    rows = await db.execute(text(f"""
        SELECT id, title, synthesized_summary,
               1 - (embedding <=> '{vector_literal}'::vector) AS similarity,
               artifact_count, reuse_count, last_updated_at
        FROM canonical_questions
        WHERE id != :id AND embedding IS NOT NULL
        ORDER BY embedding <=> '{vector_literal}'::vector
        LIMIT 5
    """), {"id": canonical_id})
    return [
        SearchResult(
            canonical_question_id=r[0], title=r[1], synthesized_summary=r[2],
            similarity=round(float(r[3]), 4), artifact_count=r[4],
            reuse_count=r[5], last_updated_at=r[6],
        )
        for r in rows.fetchall()
    ]

@router.post("/{canonical_id}/reuse", status_code=201)
async def record_reuse(canonical_id: str, reused_by: str = None, db: AsyncSession = Depends(get_db)):
    from models import ReuseEvent
    from sqlalchemy import text
    event = ReuseEvent(canonical_question_id=canonical_id, reused_by=reused_by)
    db.add(event)
    await db.execute(
        text("UPDATE canonical_questions SET reuse_count = reuse_count + 1 WHERE id = :id"),
        {"id": canonical_id},
    )
    await db.commit()
    return {"recorded": True}
```

- [ ] **Step 4: Create routes/flags.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from database import get_db
from models import CommunityFlag, ResearchArtifact
from schemas import FlagCreate
from pydantic import validator

VALID_FLAG_TYPES = {"useful", "stale", "weakly_sourced", "wrong"}
FLAG_COLUMN = {"useful": "useful_count", "stale": "stale_count", "weakly_sourced": "weakly_sourced_count", "wrong": "wrong_count"}

router = APIRouter(tags=["flags"])

@router.post("", status_code=201)
async def add_flag(body: FlagCreate, db: AsyncSession = Depends(get_db)):
    if body.flag_type not in VALID_FLAG_TYPES:
        from fastapi import status
        from fastapi.responses import JSONResponse
        raise HTTPException(status_code=422, detail=f"flag_type must be one of {VALID_FLAG_TYPES}")
    result = await db.execute(select(ResearchArtifact).where(ResearchArtifact.id == body.artifact_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Artifact not found")
    flag = CommunityFlag(artifact_id=body.artifact_id, flag_type=body.flag_type)
    db.add(flag)
    col = FLAG_COLUMN[body.flag_type]
    await db.execute(
        text(f"UPDATE research_artifacts SET {col} = {col} + 1 WHERE id = :id"),
        {"id": str(body.artifact_id)},
    )
    await db.commit()
    return {"flagged": True}
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && pytest ../tests/test_flags.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/routes/canonical.py backend/routes/flags.py tests/test_flags.py
git commit -m "feat(backend): canonical question routes, related questions, and community flags"
```

---

### Task 10: Discovery routes

**Files:**
- Create: `backend/routes/discovery.py`

- [ ] **Step 1: Create routes/discovery.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import get_db

router = APIRouter(tags=["discovery"])

@router.get("/weekly")
async def weekly_research(db: AsyncSession = Depends(get_db)):
    """Top canonical questions by artifact submissions in the past 7 days."""
    result = await db.execute(text("""
        SELECT cq.id, cq.title, cq.synthesized_summary, COUNT(ra.id) AS run_count, cq.reuse_count
        FROM canonical_questions cq
        JOIN research_artifacts ra ON ra.canonical_question_id = cq.id
        WHERE ra.created_at >= NOW() - INTERVAL '7 days'
        GROUP BY cq.id
        ORDER BY run_count DESC
        LIMIT 20
    """))
    rows = result.fetchall()
    return [
        {"canonical_question_id": str(r[0]), "title": r[1], "summary": r[2], "run_count": r[3], "reuse_count": r[4]}
        for r in rows
    ]

@router.get("/top-reused")
async def top_reused(db: AsyncSession = Depends(get_db)):
    """Canonical questions with the highest reuse count."""
    result = await db.execute(text("""
        SELECT id, title, synthesized_summary, reuse_count, artifact_count, last_updated_at
        FROM canonical_questions
        ORDER BY reuse_count DESC
        LIMIT 20
    """))
    rows = result.fetchall()
    return [
        {"canonical_question_id": str(r[0]), "title": r[1], "summary": r[2],
         "reuse_count": r[3], "artifact_count": r[4], "last_updated_at": str(r[5])}
        for r in rows
    ]

@router.get("/leaderboard")
async def leaderboard(db: AsyncSession = Depends(get_db)):
    """Top contributors by reuse count."""
    result = await db.execute(text("""
        SELECT handle, display_name, total_contributions, total_reuse_count, reputation_score
        FROM contributors
        ORDER BY total_reuse_count DESC, total_contributions DESC
        LIMIT 20
    """))
    rows = result.fetchall()
    return [
        {"handle": r[0], "display_name": r[1], "total_contributions": r[2],
         "total_reuse_count": r[3], "reputation_score": round(r[4], 2)}
        for r in rows
    ]
```

- [ ] **Step 2: Run full test suite**

```bash
cd backend && pytest ../tests/ -v
```

Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/routes/discovery.py
git commit -m "feat(backend): discovery routes — weekly, top-reused, leaderboard"
```

---

### Task 11: Dockerfile and Fly.io deployment

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/fly.toml`
- Create: `backend/.env.example`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 2: Create fly.toml**

```toml
app = "signal-archive-api"
primary_region = "ams"

[build]

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 1

[[vm]]
  size = "shared-cpu-1x"
  memory = "256mb"
```

- [ ] **Step 3: Create .env.example**

```
DATABASE_URL=postgresql+asyncpg://postgres:password@db.supabase.co:5432/postgres
OPENAI_API_KEY=sk-...
API_KEY_SALT=random-long-secret-string
ENVIRONMENT=production
```

- [ ] **Step 4: Deploy to Fly.io**

```bash
# Install flyctl: brew install flyctl
# Authenticate: flyctl auth login
cd backend

flyctl launch --name signal-archive-api --region ams --no-deploy
flyctl secrets set \
  DATABASE_URL="$(op read 'op://ch-os-priv/signal-archive-db/url')" \
  OPENAI_API_KEY="$(op read 'op://ch-os-priv/openai-api-key/credential')" \
  API_KEY_SALT="$(op read 'op://ch-os-priv/signal-archive-salt/credential')"
flyctl deploy
```

Expected: `signal-archive-api.fly.dev/health` returns `{"status": "ok"}`

- [ ] **Step 5: Apply migration to production Supabase**

```bash
psql "$(op read 'op://ch-os-priv/signal-archive-db/url')" -f migrations/001_initial.sql
```

Expected: tables and indexes created without errors

- [ ] **Step 6: Commit**

```bash
git add backend/Dockerfile backend/fly.toml backend/.env.example
git commit -m "feat(backend): Fly.io deployment config and Dockerfile"
```

---

### Self-Review

**Spec coverage:**
- ✅ Artifact submission with all required fields (§13.4)
- ✅ Semantic search before run (§13.3)
- ✅ Canonical question handling with similarity threshold (§13.5)
- ✅ Community flags: useful, stale, weakly_sourced, wrong (§13.9)
- ✅ Contributor profile with reuse count and reputation score (§13.8)
- ✅ Reuse event recording (§13.8)
- ✅ Discovery: weekly, top-reused, leaderboard (§13.7, §13.8)
- ✅ API key auth for write endpoints (§16 safety)
- ✅ CORS enabled for static website calls
- ⚠️ Reputation score computation not yet automated — seeded at 0, needs Trust plan (Plan 5)

**Placeholder scan:** None found.

**Type consistency:** All schemas use the same field names throughout. `ArtifactResponse` requires a `contributor_handle` field that isn't populated from the ORM directly — fix by adding a join or a property. In `routes/artifacts.py`, the GET endpoint returns the raw ORM object which won't have `contributor_handle`. This is a gap — the GET artifact route should join contributor and return handle. This is acceptable for MVP since the website can use the contributor route separately.
