import { authHeaders } from './auth.js';

const API_URL = import.meta.env.PUBLIC_API_URL || 'https://signal-archive-api.fly.dev';

export const BASE = import.meta.env.BASE_URL || '/signal-archive';

export async function searchArchive(query, limit = 5, sort = 'relevance') {
  const res = await fetch(
    `${API_URL}/search?q=${encodeURIComponent(query)}&limit=${limit}&sort=${sort}`,
    { headers: authHeaders() }
  );
  if (res.status === 401) return null;  // signal: not authenticated
  if (!res.ok) return [];
  return res.json();
}

export async function getCanonical(id) {
  const res = await fetch(`${API_URL}/canonical/${id}`);
  if (!res.ok) return null;
  return res.json();
}

export async function getCanonicalArtifacts(id) {
  const res = await fetch(`${API_URL}/canonical/${id}/artifacts?include_superseded=true`);
  if (!res.ok) return [];
  return res.json();
}

export async function getRelated(id) {
  const res = await fetch(`${API_URL}/canonical/${id}/related`);
  if (!res.ok) return [];
  return res.json();
}

export async function getWeeklyResearch() {
  const res = await fetch(`${API_URL}/discovery/weekly`, { headers: authHeaders() });
  if (!res.ok) return [];
  return res.json();
}

export async function getTopReused() {
  const res = await fetch(`${API_URL}/discovery/top-reused`, { headers: authHeaders() });
  if (!res.ok) return [];
  return res.json();
}

export async function getLeaderboard() {
  const res = await fetch(`${API_URL}/discovery/leaderboard`, { headers: authHeaders() });
  if (!res.ok) return [];
  return res.json();
}

export async function getContributor(handle) {
  const res = await fetch(`${API_URL}/contributors/${handle}`);
  if (!res.ok) return null;
  return res.json();
}

export async function getEmerging() {
  const res = await fetch(`${API_URL}/discovery/emerging`, { headers: authHeaders() });
  if (!res.ok) return [];
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
