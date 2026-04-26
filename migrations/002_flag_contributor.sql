-- Migration 002: add contributor_id to community_flags + unique dedup constraint
-- Run once against the production DB (Supabase SQL editor or psql).

ALTER TABLE community_flags
    ADD COLUMN IF NOT EXISTS contributor_id UUID REFERENCES contributors(id) ON DELETE SET NULL;

-- Partial unique index: one flag type per contributor per artifact.
-- NULL contributor_id (legacy rows) are excluded from the constraint.
CREATE UNIQUE INDEX IF NOT EXISTS uq_flag_per_contributor
    ON community_flags (artifact_id, flag_type, contributor_id)
    WHERE contributor_id IS NOT NULL;
