-- Self-referential FK so a new artifact can mark an older one as superseded.
-- Sparse index covers the FK without paying for NULL rows (most artifacts won't supersede anything).
ALTER TABLE research_artifacts
    ADD COLUMN IF NOT EXISTS supersedes_id UUID REFERENCES research_artifacts(id);

CREATE INDEX IF NOT EXISTS research_artifacts_supersedes_idx
    ON research_artifacts (supersedes_id)
    WHERE supersedes_id IS NOT NULL;
