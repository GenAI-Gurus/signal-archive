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
