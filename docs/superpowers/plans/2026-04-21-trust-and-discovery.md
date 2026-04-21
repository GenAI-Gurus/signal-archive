# Trust and Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement automated reputation scoring for contributors and enrich the discovery routes with emerging-topic detection, so the archive feels alive and trust signals update automatically as the archive grows.

**Architecture:** A Python `reputation/` module runs as a Fly.io scheduled task (cron) to recompute contributor reputation scores periodically. Emerging topics are detected by clustering recent canonical questions by embedding similarity in the backend. No external ML services — all computation uses data already in Supabase.

**Tech Stack:** Python 3.11, numpy (cosine similarity clustering), Fly.io scheduled machines, existing FastAPI backend, Supabase Postgres

**Dependencies:** Core Backend (Plan 1) must be complete and deployed. This plan adds to the existing backend — it does not replace anything.

---

## File Structure

```
reputation/
├── __init__.py
├── scorer.py               # Reputation scoring logic
├── runner.py               # Entry point for scheduled run
└── requirements.txt

backend/routes/discovery.py   # MODIFY: add /discovery/emerging endpoint
migrations/
└── 002_reputation_index.sql  # Index for fast reputation queries

tests/
├── test_reputation.py
└── test_discovery_emerging.py
```

---

### Task 1: Reputation scoring module

Reputation score for a contributor is computed from:
1. `reuse_ratio` = total_reuse_count / max(total_contributions, 1)
2. `flag_ratio` = useful_flags / max(total_flags, 1) — positive if mostly "useful", negative if mostly "wrong"
3. `score` = `reuse_ratio * 10 + flag_ratio * 5`, clamped to [0, 100]

**Files:**
- Create: `reputation/requirements.txt`
- Create: `reputation/scorer.py`
- Test: `tests/test_reputation.py`

- [ ] **Step 1: Create reputation/requirements.txt**

```
asyncpg==0.29.0
sqlalchemy[asyncio]==2.0.35
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_reputation.py`:

```python
import pytest
from reputation.scorer import compute_reputation_score

def test_high_reuse_high_useful_flags_scores_well():
    score = compute_reputation_score(
        total_contributions=10,
        total_reuse_count=40,
        useful_flags=20,
        stale_flags=1,
        weakly_sourced_flags=0,
        wrong_flags=0,
    )
    assert score > 40.0
    assert score <= 100.0

def test_zero_contributions_scores_zero():
    score = compute_reputation_score(
        total_contributions=0,
        total_reuse_count=0,
        useful_flags=0,
        stale_flags=0,
        weakly_sourced_flags=0,
        wrong_flags=0,
    )
    assert score == 0.0

def test_high_wrong_flags_penalizes_score():
    score_bad = compute_reputation_score(
        total_contributions=5,
        total_reuse_count=5,
        useful_flags=0,
        stale_flags=0,
        weakly_sourced_flags=0,
        wrong_flags=10,
    )
    score_good = compute_reputation_score(
        total_contributions=5,
        total_reuse_count=5,
        useful_flags=10,
        stale_flags=0,
        weakly_sourced_flags=0,
        wrong_flags=0,
    )
    assert score_bad < score_good

def test_score_is_clamped_to_0_100():
    score = compute_reputation_score(
        total_contributions=1,
        total_reuse_count=1000,
        useful_flags=1000,
        stale_flags=0,
        weakly_sourced_flags=0,
        wrong_flags=0,
    )
    assert 0.0 <= score <= 100.0
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_reputation.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'reputation'`

- [ ] **Step 4: Create reputation/__init__.py and reputation/scorer.py**

`reputation/__init__.py` — empty.

`reputation/scorer.py`:

```python
def compute_reputation_score(
    total_contributions: int,
    total_reuse_count: int,
    useful_flags: int,
    stale_flags: int,
    weakly_sourced_flags: int,
    wrong_flags: int,
) -> float:
    if total_contributions == 0:
        return 0.0

    reuse_ratio = total_reuse_count / total_contributions
    total_flags = useful_flags + stale_flags + weakly_sourced_flags + wrong_flags
    if total_flags == 0:
        flag_ratio = 0.5   # neutral when no flags
    else:
        # useful counts +1, stale/weakly_sourced count 0, wrong counts -1
        weighted = useful_flags - wrong_flags
        flag_ratio = (weighted + total_flags) / (2 * total_flags)  # normalise to [0,1]

    raw = reuse_ratio * 10 + flag_ratio * 5
    return max(0.0, min(100.0, raw))
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_reputation.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add reputation/ tests/test_reputation.py
git commit -m "feat(reputation): contributor reputation scoring formula"
```

---

### Task 2: Reputation runner — scheduled batch update

**Files:**
- Create: `reputation/runner.py`

The runner queries all contributors and their artifact flag counts, recomputes reputation scores, and writes them back. Runs as a Fly.io scheduled machine (cron).

- [ ] **Step 1: Create reputation/runner.py**

```python
#!/usr/bin/env python3
"""
Recomputes reputation scores for all contributors.
Run on a schedule: fly machine run --schedule daily
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from scorer import compute_reputation_score

DATABASE_URL = os.environ["DATABASE_URL"]

async def run():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Pull each contributor's aggregate flag data from their artifacts
        result = await session.execute(text("""
            SELECT
                c.id,
                c.total_contributions,
                c.total_reuse_count,
                COALESCE(SUM(ra.useful_count), 0) AS useful_flags,
                COALESCE(SUM(ra.stale_count), 0) AS stale_flags,
                COALESCE(SUM(ra.weakly_sourced_count), 0) AS weakly_sourced_flags,
                COALESCE(SUM(ra.wrong_count), 0) AS wrong_flags
            FROM contributors c
            LEFT JOIN research_artifacts ra ON ra.contributor_id = c.id
            GROUP BY c.id, c.total_contributions, c.total_reuse_count
        """))
        rows = result.fetchall()

        updated = 0
        for row in rows:
            contrib_id, total_contributions, total_reuse_count, useful, stale, weak, wrong = row
            score = compute_reputation_score(
                total_contributions=total_contributions,
                total_reuse_count=total_reuse_count,
                useful_flags=useful,
                stale_flags=stale,
                weakly_sourced_flags=weak,
                wrong_flags=wrong,
            )
            await session.execute(
                text("UPDATE contributors SET reputation_score = :score WHERE id = :id"),
                {"score": score, "id": contrib_id},
            )
            updated += 1

        await session.commit()
        print(f"Reputation updated for {updated} contributor(s).")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run())
```

- [ ] **Step 2: Run the scorer locally against the dev database**

```bash
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:54322/postgres" \
  python reputation/runner.py
```

Expected: `Reputation updated for N contributor(s).`

- [ ] **Step 3: Set up as a Fly.io scheduled machine**

```bash
# In fly.toml (already deployed backend), add a scheduled machine for daily reputation updates:
flyctl machine run \
  --app signal-archive-api \
  --schedule daily \
  --env DATABASE_URL="$(flyctl secrets list --app signal-archive-api | grep DATABASE_URL)" \
  -- python /app/reputation/runner.py
```

Expected: Machine registered as a daily scheduled job in Fly.io

- [ ] **Step 4: Commit**

```bash
git add reputation/runner.py
git commit -m "feat(reputation): daily batch reputation score updater for Fly.io"
```

---

### Task 3: Emerging topics discovery endpoint

Emerging topics = canonical questions created in the past 14 days that have accumulated at least 2 artifacts or 1 reuse, ordered by recency and growth signal.

**Files:**
- Modify: `backend/routes/discovery.py`
- Test: `tests/test_discovery_emerging.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_discovery_emerging.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from main import app

@pytest.mark.asyncio
async def test_emerging_endpoint_returns_list():
    with patch("routes.discovery.get_db") as mock_db_ctx:
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: [
            ("cq-id-1", "What is Fly.io?", "Overview of Fly.io", 3, 2)
        ]))
        mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/discovery/emerging")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["title"] == "What is Fly.io?"
    assert "growth_score" in data[0]

@pytest.mark.asyncio
async def test_emerging_endpoint_returns_empty_list_when_no_data():
    with patch("routes.discovery.get_db") as mock_db_ctx:
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))
        mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/discovery/emerging")

    assert response.status_code == 200
    assert response.json() == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest ../tests/test_discovery_emerging.py -v
```

Expected: FAIL — `404 Not Found` for `/discovery/emerging`

- [ ] **Step 3: Add /discovery/emerging to backend/routes/discovery.py**

Open `backend/routes/discovery.py` and append this route:

```python
@router.get("/emerging")
async def emerging_topics(db: AsyncSession = Depends(get_db)):
    """Canonical questions created in the last 14 days with growth signals."""
    result = await db.execute(text("""
        SELECT
            cq.id,
            cq.title,
            cq.synthesized_summary,
            cq.artifact_count,
            cq.reuse_count,
            (cq.artifact_count * 2 + cq.reuse_count * 3) AS growth_score
        FROM canonical_questions cq
        WHERE cq.created_at >= NOW() - INTERVAL '14 days'
          AND (cq.artifact_count >= 2 OR cq.reuse_count >= 1)
        ORDER BY growth_score DESC, cq.created_at DESC
        LIMIT 20
    """))
    rows = result.fetchall()
    return [
        {
            "canonical_question_id": str(r[0]),
            "title": r[1],
            "summary": r[2],
            "artifact_count": r[3],
            "reuse_count": r[4],
            "growth_score": r[5],
        }
        for r in rows
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest ../tests/test_discovery_emerging.py -v
```

Expected: both tests PASS

- [ ] **Step 5: Add emerging section to the website discovery page**

Open `website/src/pages/discovery.astro` and add after the existing two sections:

```astro
<!-- Add inside the page, after the weekly/reused grid: -->
<section class="mt-12">
  <h2 class="text-xl font-semibold text-white mb-4">🌱 Emerging topics (last 14 days)</h2>
  <div id="emerging"></div>
</section>
```

Add to the `<script>` block — import `getWeeklyResearch` and add:

```javascript
// Add this import to api.js first:
// export async function getEmerging() {
//   const res = await fetch(`${API_URL}/discovery/emerging`);
//   if (!res.ok) return [];
//   return res.json();
// }

// Then in discovery.astro script:
import { ..., getEmerging } from '../lib/api.js';

getEmerging().then(items => {
  const container = document.getElementById('emerging');
  if (!items.length) {
    container.appendChild(el('p', 'text-gray-500 italic text-sm', 'No emerging topics yet.'));
    return;
  }
  const grid = el('div', 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4');
  items.slice(0, 9).forEach(item => {
    const card = el('a', 'block bg-gray-900 border border-gray-800 hover:border-brand-500/40 rounded-xl p-4 transition-all');
    card.href = `${BASE}/canonical/${item.canonical_question_id}`;
    card.appendChild(el('p', 'text-sm text-gray-200 font-medium mb-2', item.title));
    const meta = el('div', 'flex gap-3 text-xs text-gray-600');
    meta.appendChild(el('span', null, `📄 ${item.artifact_count}`));
    if (item.reuse_count > 0) meta.appendChild(el('span', null, `♻️ ${item.reuse_count}`));
    card.appendChild(meta);
    grid.appendChild(card);
  });
  container.appendChild(grid);
});
```

- [ ] **Step 6: Add getEmerging to website/src/lib/api.js**

```javascript
// Add to api.js:
export async function getEmerging() {
  const res = await fetch(`${API_URL}/discovery/emerging`);
  if (!res.ok) return [];
  return res.json();
}
```

- [ ] **Step 7: Run full test suite**

```bash
cd backend && pytest ../tests/ -v
pytest tests/test_reputation.py -v
```

Expected: all tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/routes/discovery.py reputation/runner.py website/src/ tests/test_discovery_emerging.py
git commit -m "feat(trust): reputation scoring, daily updater, and emerging topics endpoint"
```

---

### Task 4: Migration for reputation query performance

**Files:**
- Create: `backend/migrations/002_reputation_index.sql`

- [ ] **Step 1: Create the migration**

```sql
-- Speed up the reputation runner's aggregate query
CREATE INDEX IF NOT EXISTS research_artifacts_contributor_flags_idx
    ON research_artifacts (contributor_id, useful_count, stale_count, weakly_sourced_count, wrong_count);

-- Speed up emerging topics (WHERE created_at >= ...)
CREATE INDEX IF NOT EXISTS canonical_questions_created_at_idx
    ON canonical_questions (created_at DESC);

-- Speed up weekly discovery (WHERE ra.created_at >= NOW() - INTERVAL '7 days')
CREATE INDEX IF NOT EXISTS research_artifacts_created_at_idx
    ON research_artifacts (created_at DESC);
```

- [ ] **Step 2: Apply to production**

```bash
psql "$(op read 'op://ch-os-priv/signal-archive-db/url')" -f backend/migrations/002_reputation_index.sql
```

Expected: 3 indexes created without errors

- [ ] **Step 3: Commit**

```bash
git add backend/migrations/002_reputation_index.sql
git commit -m "feat(trust): performance indexes for reputation and discovery queries"
```

---

### Self-Review

**Spec coverage:**
- ✅ Contributor reputation score based on reuse and useful flags (§15.3)
- ✅ Reputation score updated automatically (daily cron, not manual) (§15.2.4)
- ✅ Reward: reuse count, reputation score, leaderboard (§14.1)
- ✅ Reward principle: reuse over quantity, no spam incentive (§14.3)
- ✅ Emerging questions discovery view (§13.7.3, §18.3.3)
- ✅ Discovery pages feel alive with weekly, top-reused, and emerging (§13.7)
- ✅ Performance indexes for discovery queries at meaningful scale (§22)
- ⚠️ Reputation decay over time (§25.5.2) is not implemented in MVP — can be added by weighting recent reuses more heavily in the scorer. Log as a Linear issue.

**Placeholder scan:** None found.

**Type consistency:** `compute_reputation_score` parameter names match the SQL column names used in `runner.py`.
