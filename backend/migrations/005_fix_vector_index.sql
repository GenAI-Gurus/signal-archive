-- IVFFlat index was built on empty table (no centroids), causing ORDER BY vector distance to return 0 rows.
-- Replace with HNSW which builds incrementally and works correctly regardless of table state at creation time.

DROP INDEX IF EXISTS canonical_questions_embedding_idx;
DROP INDEX IF EXISTS research_artifacts_embedding_idx;

CREATE INDEX canonical_questions_embedding_idx
    ON canonical_questions USING hnsw (embedding vector_cosine_ops);

CREATE INDEX research_artifacts_embedding_idx
    ON research_artifacts USING hnsw (embedding vector_cosine_ops);
