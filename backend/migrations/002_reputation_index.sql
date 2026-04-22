-- Speed up the reputation runner's aggregate query
CREATE INDEX IF NOT EXISTS research_artifacts_contributor_flags_idx
    ON research_artifacts (contributor_id, useful_count, stale_count, weakly_sourced_count, wrong_count);

-- Speed up emerging topics (WHERE created_at >= ...)
CREATE INDEX IF NOT EXISTS canonical_questions_created_at_idx
    ON canonical_questions (created_at DESC);

-- Speed up weekly discovery (WHERE ra.created_at >= NOW() - INTERVAL '7 days')
CREATE INDEX IF NOT EXISTS research_artifacts_created_at_idx
    ON research_artifacts (created_at DESC);
