# Public Website Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the polished public Signal Archive website as a static Astro site deployed to GitHub Pages, with semantic search, canonical question pages, discovery views, leaderboard, and contributor profiles — all calling the live backend API from the browser.

**Architecture:** Astro with static output mode. All data fetches happen client-side. Pages are pre-rendered HTML shells that populate with live API data on load. DOMPurify is used wherever API content is inserted into the DOM as HTML. Deployed via GitHub Actions to GitHub Pages on every push to `main`.

**Tech Stack:** Astro 4.x, vanilla JS, Tailwind CSS, DOMPurify, GitHub Pages, GitHub Actions

**Security note:** All client-side DOM insertions that render API data use either `textContent` (for plain text) or `DOMPurify.sanitize()` (when HTML structure is needed). This prevents XSS even if the API returns unexpected content.

**Dependencies:** Core Backend (Plan 1) must be deployed. No dependency on sanitizer or worker plans.

---

## File Structure

```
website/
├── astro.config.mjs
├── package.json
├── tailwind.config.mjs
├── public/
│   └── favicon.svg
└── src/
    ├── layouts/
    │   └── Base.astro
    ├── components/
    │   ├── SearchBox.astro
    │   └── ArtifactCard.astro
    ├── pages/
    │   ├── index.astro
    │   ├── search.astro
    │   ├── canonical/[id].astro
    │   ├── discovery.astro
    │   ├── leaderboard.astro
    │   ├── about.astro
    │   └── contributor/[handle].astro
    └── lib/
        └── api.js

.github/
└── workflows/
    └── deploy-website.yml
```

---

### Task 1: Astro project scaffold

**Files:**
- Create: `website/package.json`
- Create: `website/astro.config.mjs`
- Create: `website/tailwind.config.mjs`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "signal-archive-website",
  "type": "module",
  "version": "0.1.0",
  "scripts": {
    "dev": "astro dev",
    "build": "astro build",
    "preview": "astro preview"
  },
  "dependencies": {
    "astro": "^4.15.0",
    "@astrojs/tailwind": "^5.1.0",
    "tailwindcss": "^3.4.10",
    "dompurify": "^3.1.6"
  }
}
```

- [ ] **Step 2: Create astro.config.mjs**

```javascript
import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  output: 'static',
  site: 'https://carloshvp.github.io',
  base: '/signal-archive',
  integrations: [tailwind()],
});
```

- [ ] **Step 3: Create tailwind.config.mjs**

```javascript
export default {
  content: ['./src/**/*.{astro,html,js}'],
  theme: {
    extend: {
      colors: {
        brand: {
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          900: '#1e1b4b',
        },
      },
    },
  },
};
```

- [ ] **Step 4: Install and verify dev server starts**

```bash
cd website && npm install
npm run dev
```

Expected: Astro dev server starts at `http://localhost:4321`, no errors

- [ ] **Step 5: Commit**

```bash
git add website/
git commit -m "feat(website): Astro project scaffold with Tailwind and DOMPurify"
```

---

### Task 2: API client and base layout

**Files:**
- Create: `website/src/lib/api.js`
- Create: `website/src/layouts/Base.astro`

- [ ] **Step 1: Create src/lib/api.js**

```javascript
const API_URL = import.meta.env.PUBLIC_API_URL || 'https://signal-archive-api.fly.dev';

export const BASE = import.meta.env.BASE_URL || '/signal-archive';

export async function searchArchive(query, limit = 5) {
  const res = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  if (!res.ok) return [];
  return res.json();
}

export async function getCanonical(id) {
  const res = await fetch(`${API_URL}/canonical/${id}`);
  if (!res.ok) return null;
  return res.json();
}

export async function getCanonicalArtifacts(id) {
  const res = await fetch(`${API_URL}/canonical/${id}/artifacts`);
  if (!res.ok) return [];
  return res.json();
}

export async function getRelated(id) {
  const res = await fetch(`${API_URL}/canonical/${id}/related`);
  if (!res.ok) return [];
  return res.json();
}

export async function getWeeklyResearch() {
  const res = await fetch(`${API_URL}/discovery/weekly`);
  if (!res.ok) return [];
  return res.json();
}

export async function getTopReused() {
  const res = await fetch(`${API_URL}/discovery/top-reused`);
  if (!res.ok) return [];
  return res.json();
}

export async function getLeaderboard() {
  const res = await fetch(`${API_URL}/discovery/leaderboard`);
  if (!res.ok) return [];
  return res.json();
}

export async function getContributor(handle) {
  const res = await fetch(`${API_URL}/contributors/${handle}`);
  if (!res.ok) return null;
  return res.json();
}

export async function submitFlag(artifactId, flagType) {
  const res = await fetch(`${API_URL}/flags`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ artifact_id: artifactId, flag_type: flagType }),
  });
  return res.ok;
}

/** Safe DOM helper — creates an element, sets textContent, adds classes */
export function el(tag, classes, text) {
  const e = document.createElement(tag);
  if (classes) e.className = classes;
  if (text !== undefined) e.textContent = text;
  return e;
}

/** Anchor with safe textContent */
export function link(href, classes, text) {
  const a = document.createElement('a');
  a.href = href;
  a.className = classes;
  a.textContent = text;
  return a;
}
```

- [ ] **Step 2: Create src/layouts/Base.astro**

```astro
---
export interface Props {
  title: string;
  description?: string;
}
const { title, description = 'Signal Archive — public memory for deep research' } = Astro.props;
const base = import.meta.env.BASE_URL || '/signal-archive';
---

<!DOCTYPE html>
<html lang="en" class="bg-gray-950 text-gray-100">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} | Signal Archive</title>
  <meta name="description" content={description} />
</head>
<body class="min-h-screen flex flex-col">
  <nav class="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
    <a href={base + '/'} class="text-lg font-bold text-brand-400 font-mono">signal-archive</a>
    <div class="flex gap-6 text-sm text-gray-400">
      <a href={base + '/search'} class="hover:text-white">Search</a>
      <a href={base + '/discovery'} class="hover:text-white">Discovery</a>
      <a href={base + '/leaderboard'} class="hover:text-white">Leaderboard</a>
      <a href={base + '/about'} class="hover:text-white">About</a>
      <a href="https://github.com/carloshvp/signal-archive" target="_blank" class="hover:text-white">GitHub</a>
    </div>
  </nav>
  <main class="flex-1 container mx-auto px-6 py-10 max-w-5xl">
    <slot />
  </main>
  <footer class="border-t border-gray-800 px-6 py-6 text-center text-xs text-gray-600">
    Signal Archive · Powered by <a href="https://genaigurus.com" class="hover:text-gray-400">GenAI Gurus</a>
    · <a href="https://github.com/carloshvp/signal-archive" class="hover:text-gray-400">Open source</a>
  </footer>
</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add website/src/
git commit -m "feat(website): API client with safe DOM helpers and base layout"
```

---

### Task 3: Homepage

**Files:**
- Create: `website/src/pages/index.astro`
- Create: `website/src/components/SearchBox.astro`

- [ ] **Step 1: Create src/components/SearchBox.astro**

```astro
---
export interface Props {
  large?: boolean;
}
const { large = false } = Astro.props;
const base = import.meta.env.BASE_URL || '/signal-archive';
---

<form action={base + '/search'} method="get" class="w-full flex gap-2">
  <input
    type="search"
    name="q"
    placeholder="Search public research questions..."
    class={`flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-500 ${large ? 'py-4 text-lg' : 'py-3'}`}
  />
  <button
    type="submit"
    class={`bg-brand-600 hover:bg-brand-500 text-white font-semibold rounded-lg transition-colors ${large ? 'px-8 py-4' : 'px-6 py-3'}`}
  >
    Search
  </button>
</form>
```

- [ ] **Step 2: Create src/pages/index.astro**

```astro
---
import Base from '../layouts/Base.astro';
import SearchBox from '../components/SearchBox.astro';
const base = import.meta.env.BASE_URL || '/signal-archive';
---

<Base title="Public Memory for Deep Research">
  <section class="text-center py-20">
    <div class="inline-block bg-brand-900/30 border border-brand-500/30 rounded-full px-4 py-1 text-xs text-brand-400 mb-6">
      Powered by GenAI Gurus · Agent-first public archive
    </div>
    <h1 class="text-5xl font-bold text-white mb-4 leading-tight">
      Search before your agents<br />research again.
    </h1>
    <p class="text-xl text-gray-400 mb-10 max-w-2xl mx-auto">
      Signal Archive is a public memory layer for deep research. Agents and founders discover
      reusable research before spending more compute.
    </p>
    <div class="max-w-2xl mx-auto"><SearchBox large={true} /></div>
  </section>

  <section class="mt-16 grid grid-cols-1 md:grid-cols-2 gap-8">
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h2 class="text-lg font-semibold mb-4 text-gray-200">🔥 Researched this week</h2>
      <ul id="weekly-list" class="space-y-3 text-sm text-gray-400">
        <li class="bg-gray-800 rounded h-5 animate-pulse"></li>
        <li class="bg-gray-800 rounded h-5 animate-pulse w-4/5"></li>
        <li class="bg-gray-800 rounded h-5 animate-pulse w-3/4"></li>
      </ul>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h2 class="text-lg font-semibold mb-4 text-gray-200">♻️ Most reused</h2>
      <ul id="reused-list" class="space-y-3 text-sm text-gray-400">
        <li class="bg-gray-800 rounded h-5 animate-pulse"></li>
        <li class="bg-gray-800 rounded h-5 animate-pulse w-4/5"></li>
        <li class="bg-gray-800 rounded h-5 animate-pulse w-3/4"></li>
      </ul>
    </div>
  </section>

  <section class="mt-20 text-center bg-brand-900/20 border border-brand-500/20 rounded-2xl p-12">
    <h2 class="text-2xl font-bold text-white mb-4">Ready to stop duplicating research?</h2>
    <p class="text-gray-400 mb-8">Install the Claude Code integration and start contributing automatically.</p>
    <a href="https://github.com/carloshvp/signal-archive" target="_blank"
       class="bg-brand-600 hover:bg-brand-500 text-white font-semibold px-8 py-3 rounded-lg transition-colors">
      Get started on GitHub
    </a>
  </section>
</Base>

<script>
  import { getWeeklyResearch, getTopReused, el, link, BASE } from '../lib/api.js';

  function renderList(containerId, items, hrefFn, labelFn, badgeFn) {
    const list = document.getElementById(containerId);
    list.replaceChildren();
    if (!items.length) {
      const li = document.createElement('li');
      li.textContent = 'Nothing yet — be the first to contribute!';
      li.className = 'text-gray-600 italic';
      list.appendChild(li);
      return;
    }
    items.slice(0, 5).forEach(item => {
      const li = document.createElement('li');
      const a = link(hrefFn(item), 'text-brand-400 hover:text-brand-300 hover:underline', labelFn(item));
      const badge = el('span', 'ml-2 text-xs text-gray-600', badgeFn(item));
      li.appendChild(a);
      li.appendChild(badge);
      list.appendChild(li);
    });
  }

  getWeeklyResearch().then(items =>
    renderList('weekly-list', items,
      i => `${BASE}/canonical/${i.canonical_question_id}`,
      i => i.title,
      i => `${i.run_count} runs`
    )
  );

  getTopReused().then(items =>
    renderList('reused-list', items,
      i => `${BASE}/canonical/${i.canonical_question_id}`,
      i => i.title,
      i => `♻️ ${i.reuse_count}`
    )
  );
</script>
```

- [ ] **Step 3: Verify in dev browser**

```bash
cd website && npm run dev
# Open http://localhost:4321/signal-archive/
```

Expected: Hero renders, search form present, discovery lists show skeletons then populate

- [ ] **Step 4: Commit**

```bash
git add website/src/pages/index.astro website/src/components/SearchBox.astro
git commit -m "feat(website): homepage with hero, search, and discovery widgets"
```

---

### Task 4: Search results page

**Files:**
- Create: `website/src/pages/search.astro`

- [ ] **Step 1: Create src/pages/search.astro**

```astro
---
import Base from '../layouts/Base.astro';
import SearchBox from '../components/SearchBox.astro';
---

<Base title="Search" description="Search the Signal Archive for public research">
  <div class="max-w-3xl mx-auto">
    <h1 class="text-2xl font-bold text-white mb-6">Search the Archive</h1>
    <SearchBox />
    <div id="results" class="mt-8 space-y-4"></div>
    <div id="empty" class="hidden mt-8 text-center text-gray-500 py-12">
      <p class="text-lg">No results found.</p>
      <p class="text-sm mt-2">Fresh research territory — be the first to contribute!</p>
    </div>
  </div>
</Base>

<script>
  import { searchArchive, el, link, BASE } from '../lib/api.js';

  const params = new URLSearchParams(window.location.search);
  const query = params.get('q');
  const resultsEl = document.getElementById('results');
  const emptyEl = document.getElementById('empty');

  if (query) {
    const input = document.querySelector('input[name="q"]');
    if (input) input.value = query;
    document.title = `"${query}" — Signal Archive`;

    // Loading skeletons
    resultsEl.replaceChildren();
    for (let i = 0; i < 3; i++) {
      const card = el('div', 'bg-gray-900 border border-gray-800 rounded-xl p-6 animate-pulse');
      card.appendChild(el('div', 'h-5 bg-gray-800 rounded w-3/4 mb-3'));
      card.appendChild(el('div', 'h-4 bg-gray-800 rounded w-full mb-2'));
      card.appendChild(el('div', 'h-4 bg-gray-800 rounded w-2/3'));
      resultsEl.appendChild(card);
    }

    searchArchive(query, 10).then(results => {
      resultsEl.replaceChildren();
      if (!results.length) {
        emptyEl.classList.remove('hidden');
        return;
      }
      results.forEach(r => {
        const pct = Math.round(r.similarity * 100);
        const card = el('a', 'block bg-gray-900 border border-gray-800 hover:border-brand-500/50 rounded-xl p-6 transition-all group');
        card.href = `${BASE}/canonical/${r.canonical_question_id}`;

        const header = el('div', 'flex items-start justify-between gap-4');
        const title = el('h3', 'font-semibold text-white group-hover:text-brand-400 transition-colors', r.title);
        const badge = el('span',
          `shrink-0 text-xs font-mono px-2 py-1 rounded-full border ${pct >= 85 ? 'bg-green-900/30 border-green-700/40 text-green-400' : 'bg-gray-800 border-gray-700 text-gray-400'}`,
          `${pct}%`
        );
        header.appendChild(title);
        header.appendChild(badge);
        card.appendChild(header);

        if (r.synthesized_summary) {
          card.appendChild(el('p', 'mt-2 text-sm text-gray-400', r.synthesized_summary.substring(0, 200)));
        }

        const meta = el('div', 'mt-3 flex gap-4 text-xs text-gray-600');
        meta.appendChild(el('span', null, `📄 ${r.artifact_count} artifact${r.artifact_count !== 1 ? 's' : ''}`));
        if (r.reuse_count > 0) {
          meta.appendChild(el('span', null, `♻️ ${r.reuse_count} reuses`));
        }
        card.appendChild(meta);
        resultsEl.appendChild(card);
      });
    });
  }
</script>
```

- [ ] **Step 2: Test in browser**

```bash
# Open http://localhost:4321/signal-archive/search?q=vector+databases
```

Expected: Query pre-filled, skeletons appear, then results (or empty state)

- [ ] **Step 3: Commit**

```bash
git add website/src/pages/search.astro
git commit -m "feat(website): search results page with safe DOM construction"
```

---

### Task 5: Canonical question page

**Files:**
- Create: `website/src/pages/canonical/[id].astro`

- [ ] **Step 1: Create src/pages/canonical/[id].astro**

```astro
---
import Base from '../../layouts/Base.astro';
---

<Base title="Research Question">
  <div id="loading" class="animate-pulse space-y-4 max-w-4xl mx-auto">
    <div class="h-8 bg-gray-800 rounded w-3/4"></div>
    <div class="h-4 bg-gray-800 rounded w-full"></div>
    <div class="h-4 bg-gray-800 rounded w-4/5"></div>
  </div>
  <div id="content" class="hidden max-w-4xl mx-auto"></div>
  <div id="error" class="hidden text-center py-20 text-gray-500">
    Research question not found.
    <a href="/signal-archive/search" class="block mt-4 text-brand-400 hover:underline">Back to search</a>
  </div>
</Base>

<script>
  import { getCanonical, getCanonicalArtifacts, getRelated, submitFlag, el, link, BASE } from '../../lib/api.js';

  const id = window.location.pathname.split('/').filter(Boolean).pop();

  function buildProvenance(artifact) {
    const div = el('div', 'bg-gray-900 border border-gray-800 rounded-xl p-4 text-xs');
    div.appendChild(el('div', 'text-gray-500 uppercase tracking-wider mb-2 font-semibold', 'Provenance'));
    const grid = el('div', 'grid grid-cols-2 gap-1 text-gray-400');
    const date = new Date(artifact.run_date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    [
      ['🤖 Worker', artifact.worker_type],
      ['📅 Run', date],
      ['🔗 Sources', String((artifact.source_domains || []).length)],
      ['🧹 Cleaned', artifact.prompt_modified ? 'Yes' : 'No'],
    ].forEach(([label, value]) => {
      const row = el('div');
      row.appendChild(el('span', 'text-gray-500', label + ': '));
      row.appendChild(el('span', artifact.prompt_modified && label.includes('Cleaned') ? 'text-yellow-400' : 'text-gray-300', value));
      grid.appendChild(row);
    });
    div.appendChild(grid);
    return div;
  }

  function buildFlagButtons(artifactId) {
    const flags = [
      { type: 'useful', label: '👍 Useful', cls: 'text-green-400 border-green-800' },
      { type: 'stale', label: '⏰ Stale', cls: 'text-yellow-400 border-yellow-800' },
      { type: 'weakly_sourced', label: '⚠️ Weak sources', cls: 'text-orange-400 border-orange-800' },
      { type: 'wrong', label: '❌ Wrong', cls: 'text-red-400 border-red-800' },
    ];
    const container = el('div', 'flex gap-2 flex-wrap mt-4 pt-4 border-t border-gray-800');
    flags.forEach(f => {
      const btn = el('button', `text-xs border px-3 py-1 rounded-full hover:opacity-80 cursor-pointer ${f.cls}`, f.label);
      btn.addEventListener('click', async () => {
        const ok = await submitFlag(artifactId, f.type);
        if (ok) { btn.textContent = '✓ ' + f.label; btn.disabled = true; }
      });
      container.appendChild(btn);
    });
    return container;
  }

  async function load() {
    const [cq, artifacts, related] = await Promise.all([
      getCanonical(id),
      getCanonicalArtifacts(id),
      getRelated(id),
    ]);

    document.getElementById('loading').classList.add('hidden');

    if (!cq) {
      document.getElementById('error').classList.remove('hidden');
      return;
    }

    document.title = cq.title + ' | Signal Archive';
    const content = document.getElementById('content');
    content.classList.remove('hidden');

    // Title + meta
    content.appendChild(el('div', 'text-xs text-brand-400 font-mono mb-2 uppercase tracking-wider', 'Research Question'));
    content.appendChild(el('h1', 'text-3xl font-bold text-white leading-snug mb-3', cq.title));
    const metaRow = el('div', 'flex gap-4 text-sm text-gray-500 mb-8');
    metaRow.appendChild(el('span', null, `📄 ${cq.artifact_count} artifact${cq.artifact_count !== 1 ? 's' : ''}`));
    metaRow.appendChild(el('span', null, `♻️ ${cq.reuse_count} reuse${cq.reuse_count !== 1 ? 's' : ''}`));
    content.appendChild(metaRow);

    // Summary
    const summaryBox = el('div', 'bg-gray-900 border border-gray-800 rounded-xl p-6 mb-8');
    summaryBox.appendChild(el('h2', 'text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3', 'Synthesized Answer'));
    summaryBox.appendChild(el('p', 'text-gray-200 leading-relaxed', cq.synthesized_summary || 'Summary pending.'));
    content.appendChild(summaryBox);

    // Artifacts
    content.appendChild(el('h2', 'text-xl font-semibold text-white mb-4', 'Research Artifacts'));
    if (!artifacts.length) {
      content.appendChild(el('p', 'text-gray-500 italic mb-8', 'No artifacts yet.'));
    } else {
      artifacts.forEach(a => {
        const card = el('div', 'bg-gray-900 border border-gray-800 rounded-xl p-6 mb-4');
        const dateStr = new Date(a.run_date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
        card.appendChild(el('div', 'text-xs text-gray-500 font-mono mb-3', `${dateStr} · ${a.worker_type}`));
        card.appendChild(el('p', 'text-gray-200 text-sm leading-relaxed mb-4', a.short_answer));
        // Full body in pre — no HTML parsing, safe as-is
        const details = document.createElement('details');
        details.className = 'text-sm text-gray-400 mb-2';
        const summary = el('summary', 'cursor-pointer hover:text-white mb-2', 'Full research body');
        const pre = el('pre', 'bg-gray-950 rounded p-4 text-xs text-gray-400 overflow-auto max-h-96 whitespace-pre-wrap mt-2 font-mono', a.full_body);
        details.appendChild(summary);
        details.appendChild(pre);
        card.appendChild(details);
        card.appendChild(buildProvenance(a));
        card.appendChild(buildFlagButtons(a.id));
        content.appendChild(card);
      });
    }

    // Related
    content.appendChild(el('h2', 'text-xl font-semibold text-white mb-4 mt-8', 'Related Questions'));
    if (!related.length) {
      content.appendChild(el('p', 'text-gray-500 italic text-sm', 'No related questions yet.'));
    } else {
      related.forEach(r => {
        const a = link(
          `${BASE}/canonical/${r.canonical_question_id}`,
          'block bg-gray-900 border border-gray-800 hover:border-brand-500/40 rounded-lg px-4 py-3 text-sm text-gray-300 hover:text-white transition-colors mb-2',
          r.title
        );
        const badge = el('span', 'text-xs text-gray-600 ml-2', `${Math.round(r.similarity * 100)}% similar`);
        a.appendChild(badge);
        content.appendChild(a);
      });
    }
  }

  load();
</script>
```

- [ ] **Step 2: Test with a real canonical ID**

```bash
# Get an ID: curl https://signal-archive-api.fly.dev/discovery/top-reused | python3 -m json.tool
# Open: http://localhost:4321/signal-archive/canonical/<id>
```

Expected: Question title, summary, artifact cards with full body in collapsible pre, flag buttons, related links

- [ ] **Step 3: Commit**

```bash
git add website/src/pages/canonical/
git commit -m "feat(website): canonical question page with provenance, full body, and flag buttons"
```

---

### Task 6: Discovery, Leaderboard, About, and Contributor pages

**Files:**
- Create: `website/src/pages/discovery.astro`
- Create: `website/src/pages/leaderboard.astro`
- Create: `website/src/pages/about.astro`
- Create: `website/src/pages/contributor/[handle].astro`

- [ ] **Step 1: Create src/pages/discovery.astro**

```astro
---
import Base from '../layouts/Base.astro';
---

<Base title="Discovery">
  <h1 class="text-3xl font-bold text-white mb-2">Discovery</h1>
  <p class="text-gray-400 mb-10">What people are researching and which artifacts are most reused.</p>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
    <section>
      <h2 class="text-xl font-semibold text-white mb-4">🔥 Researched this week</h2>
      <div id="weekly"></div>
    </section>
    <section>
      <h2 class="text-xl font-semibold text-white mb-4">♻️ Most reused</h2>
      <div id="reused"></div>
    </section>
  </div>
</Base>

<script>
  import { getWeeklyResearch, getTopReused, el, link, BASE } from '../lib/api.js';

  function renderRows(containerId, items, hrefFn, titleFn, badgeFn) {
    const container = document.getElementById(containerId);
    if (!items.length) {
      container.appendChild(el('p', 'text-gray-500 italic text-sm', 'Nothing yet.'));
      return;
    }
    items.slice(0, 15).forEach((item, i) => {
      const row = el('div', 'flex items-center gap-3 bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 mb-2');
      row.appendChild(el('span', 'text-xs font-mono text-gray-600 w-5', String(i + 1)));
      row.appendChild(link(hrefFn(item), 'flex-1 text-sm text-gray-300 hover:text-white hover:underline', titleFn(item)));
      row.appendChild(el('span', 'text-xs text-gray-600', badgeFn(item)));
      container.appendChild(row);
    });
  }

  getWeeklyResearch().then(d =>
    renderRows('weekly', d, i => `${BASE}/canonical/${i.canonical_question_id}`, i => i.title, i => `${i.run_count} runs`)
  );
  getTopReused().then(d =>
    renderRows('reused', d, i => `${BASE}/canonical/${i.canonical_question_id}`, i => i.title, i => `♻️ ${i.reuse_count}`)
  );
</script>
```

- [ ] **Step 2: Create src/pages/leaderboard.astro**

```astro
---
import Base from '../layouts/Base.astro';
---

<Base title="Leaderboard">
  <h1 class="text-3xl font-bold text-white mb-2">Leaderboard</h1>
  <p class="text-gray-400 mb-10">Top contributors ranked by research others actually reused.</p>
  <div id="leaderboard" class="space-y-3"></div>
</Base>

<script>
  import { getLeaderboard, el, link, BASE } from '../lib/api.js';

  getLeaderboard().then(items => {
    const container = document.getElementById('leaderboard');
    if (!items.length) {
      container.appendChild(el('p', 'text-gray-500 italic', 'No contributors yet.'));
      return;
    }
    items.forEach((c, i) => {
      const row = el('div', 'flex items-center gap-4 bg-gray-900 border border-gray-800 rounded-xl px-6 py-4');
      row.appendChild(el('span', 'text-2xl font-bold font-mono text-gray-700 w-8', String(i + 1)));
      const info = el('div', 'flex-1');
      info.appendChild(link(`${BASE}/contributor/${c.handle}`, 'font-semibold text-white hover:text-brand-400 transition-colors', c.display_name || c.handle));
      info.appendChild(el('div', 'text-xs text-gray-600 font-mono', '@' + c.handle));
      row.appendChild(info);
      const stats = el('div', 'text-right text-xs text-gray-400 space-y-1');
      stats.appendChild(el('div', null, `📄 ${c.total_contributions}`));
      stats.appendChild(el('div', null, `♻️ ${c.total_reuse_count}`));
      row.appendChild(stats);
      container.appendChild(row);
    });
  });
</script>
```

- [ ] **Step 3: Create src/pages/about.astro**

```astro
---
import Base from '../layouts/Base.astro';
---

<Base title="About">
  <div class="max-w-3xl mx-auto">
    <h1 class="text-3xl font-bold text-white mb-4">About Signal Archive</h1>
    <p class="text-xl text-gray-300 mb-8">
      A public memory layer for deep research. Helps AI agents and founders discover
      reusable research before spending more compute.
    </p>
    <div class="space-y-8 text-gray-300">
      <section>
        <h2 class="text-xl font-semibold text-white mb-3">The problem</h2>
        <p>Deep research is rerun thousands of times in isolated agent sessions. The same public questions about AI tools, startup markets, and technology trends are researched over and over. Results stay buried in private chats and local files.</p>
      </section>
      <section>
        <h2 class="text-xl font-semibold text-white mb-3">How it works</h2>
        <ol class="list-decimal list-inside space-y-2">
          <li>Before an agent starts a research task, it searches the archive.</li>
          <li>If a relevant artifact exists, you can reuse it instead.</li>
          <li>If you run new research, a cleaned artifact is automatically contributed back.</li>
          <li>Each question gets one canonical public page with provenance and trust signals.</li>
        </ol>
      </section>
      <section>
        <h2 class="text-xl font-semibold text-white mb-3">Privacy</h2>
        <p>All artifacts are sanitized before submission. Personal names, contact info, private company context, and credentials are removed. Only public-safe, web-sourced research is accepted.</p>
      </section>
      <section>
        <h2 class="text-xl font-semibold text-white mb-3">Open source</h2>
        <p>Built and launched by <a href="https://genaigurus.com" class="text-brand-400 hover:underline">GenAI Gurus</a>.</p>
        <a href="https://github.com/carloshvp/signal-archive" target="_blank"
           class="inline-block mt-3 bg-gray-800 hover:bg-gray-700 text-white px-6 py-3 rounded-lg transition-colors">
          View on GitHub →
        </a>
      </section>
    </div>
  </div>
</Base>
```

- [ ] **Step 4: Create src/pages/contributor/[handle].astro**

```astro
---
import Base from '../../layouts/Base.astro';
---

<Base title="Contributor">
  <div id="loading" class="animate-pulse max-w-2xl mx-auto space-y-4">
    <div class="h-8 bg-gray-800 rounded w-1/2"></div>
    <div class="h-4 bg-gray-800 rounded w-1/3"></div>
  </div>
  <div id="content" class="hidden max-w-2xl mx-auto"></div>
  <div id="error" class="hidden text-center py-20 text-gray-500">Contributor not found.</div>
</Base>

<script>
  import { getContributor, el, link } from '../../lib/api.js';

  const handle = window.location.pathname.split('/').filter(Boolean).pop();

  getContributor(handle).then(c => {
    document.getElementById('loading').classList.add('hidden');
    if (!c) { document.getElementById('error').classList.remove('hidden'); return; }

    const content = document.getElementById('content');
    content.classList.remove('hidden');
    document.title = `@${c.handle} | Signal Archive`;

    const card = el('div', 'bg-gray-900 border border-gray-800 rounded-2xl p-8');

    const header = el('div', 'flex items-center gap-4 mb-6');
    const avatar = el('div', 'w-16 h-16 bg-brand-900/40 border border-brand-500/40 rounded-full flex items-center justify-center text-2xl font-bold text-brand-400',
      (c.display_name || c.handle)[0].toUpperCase());
    const nameBlock = el('div');
    nameBlock.appendChild(el('h1', 'text-2xl font-bold text-white', c.display_name || c.handle));
    nameBlock.appendChild(el('div', 'text-gray-500 font-mono text-sm', '@' + c.handle));
    header.appendChild(avatar);
    header.appendChild(nameBlock);
    card.appendChild(header);

    const stats = el('div', 'grid grid-cols-3 gap-4 text-center');
    [
      [String(c.total_contributions), 'Contributions'],
      [String(c.total_reuse_count), 'Times reused'],
      [c.reputation_score.toFixed(1), 'Reputation'],
    ].forEach(([value, label]) => {
      const stat = el('div', 'bg-gray-800 rounded-xl p-4');
      stat.appendChild(el('div', 'text-2xl font-bold text-white', value));
      stat.appendChild(el('div', 'text-xs text-gray-500 mt-1', label));
      stats.appendChild(stat);
    });
    card.appendChild(stats);
    content.appendChild(card);
  });
</script>
```

- [ ] **Step 5: Test all pages in dev**

```bash
cd website && npm run dev
# Visit: /signal-archive/discovery  /signal-archive/leaderboard  /signal-archive/about  /signal-archive/contributor/test
```

Expected: All render without errors; discovery and leaderboard show empty states until data is seeded

- [ ] **Step 6: Commit**

```bash
git add website/src/pages/
git commit -m "feat(website): discovery, leaderboard, about, and contributor profile pages"
```

---

### Task 7: GitHub Pages deployment

**Files:**
- Create: `.github/workflows/deploy-website.yml`

- [ ] **Step 1: Create the workflow file**

```yaml
name: Deploy Website

on:
  push:
    branches: [main]
    paths: ['website/**']
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: website/package-lock.json
      - run: npm ci
        working-directory: website
      - run: npm run build
        working-directory: website
        env:
          PUBLIC_API_URL: https://signal-archive-api.fly.dev
      - uses: actions/upload-pages-artifact@v3
        with:
          path: website/dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/deploy-pages@v4
        id: deployment
```

- [ ] **Step 2: Enable GitHub Pages in repo settings**

In GitHub: Settings → Pages → Source: **GitHub Actions**

- [ ] **Step 3: Push and verify deployment**

```bash
git add .github/
git commit -m "feat(website): GitHub Pages deployment via GitHub Actions"
git push origin main
```

Expected: GitHub Actions succeeds, site live at `https://carloshvp.github.io/signal-archive/`

- [ ] **Step 4: Smoke test live site**

```bash
curl -sI https://carloshvp.github.io/signal-archive/ | head -3
```

Expected: `HTTP/2 200`

---

### Self-Review

**Spec coverage:**
- ✅ Semantic search (§10.5.1, §18.1.2)
- ✅ Canonical question page with synthesized answer, trust signals, related questions (§13.6, §15.1)
- ✅ Discovery: weekly research + most reused (§13.7, §18.3.1, §18.3.2)
- ✅ Leaderboard with reuse-ranked contributors (§13.8.4)
- ✅ Community flag buttons (§13.9, §15.1.7)
- ✅ Contributor profile page (§17.3)
- ✅ Clear product headline and explanation (§18.2)
- ✅ GitHub link in nav and footer (§20)
- ✅ GenAI Gurus attribution (§18.2.8, §19.3)
- ✅ GitHub Pages hosting at $0/month (§22.1)
- ✅ XSS safety — textContent for all user-sourced text, pre for full_body, no innerHTML on API data

**Placeholder scan:** None found.

**Type consistency:** All API function names in `api.js` match imports in page scripts. `BASE` export used consistently in all cross-page links.
