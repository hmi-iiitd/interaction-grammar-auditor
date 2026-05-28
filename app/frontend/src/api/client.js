const API_BASE = 'http://localhost:8000/api';

// ── Existing Phase 5 API ────────────────────────────────────────────

export async function fetchScenarios() {
  const res = await fetch(`${API_BASE}/scenarios`);
  if (!res.ok) throw new Error(`Failed to fetch scenarios: ${res.status}`);
  return res.json();
}

export async function fetchScenario(id) {
  const res = await fetch(`${API_BASE}/scenarios/${id}`);
  if (!res.ok) throw new Error(`Scenario not found: ${id}`);
  return res.json();
}

export async function fetchAuditDetails(id) {
  const res = await fetch(`${API_BASE}/audit/${id}`);
  if (!res.ok) throw new Error(`Audit not found: ${id}`);
  return res.json();
}

export async function askQuestion(scenarioId, question) {
  const res = await fetch(`${API_BASE}/qa`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id: scenarioId, question }),
  });
  if (!res.ok) throw new Error(`Q&A failed: ${res.status}`);
  return res.json();
}

export async function fetchMarkdownReport(id) {
  const res = await fetch(`${API_BASE}/reports/${id}/markdown`);
  if (!res.ok) throw new Error(`Report not found: ${id}`);
  return res.text();
}

export async function fetchJsonReport(id) {
  const res = await fetch(`${API_BASE}/reports/${id}/json`);
  if (!res.ok) throw new Error(`Report not found: ${id}`);
  return res.json();
}

export async function runBatch() {
  const res = await fetch(`${API_BASE}/reports/batch`, { method: 'POST' });
  if (!res.ok) throw new Error(`Batch run failed: ${res.status}`);
  return res.json();
}


// ── Phase 6 Authoring API ───────────────────────────────────────────

const AUTHORING = `${API_BASE}/authoring`;

async function _post(url, body = {}) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Request failed: ${res.status}`);
  return data;
}

async function _put(url, body = {}) {
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Request failed: ${res.status}`);
  return data;
}

async function _get(url) {
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `Request failed: ${res.status}`);
  return data;
}

// Step 1: Describe
export function saveDescription(payload) {
  return _post(`${AUTHORING}/describe`, payload);
}

export function listDescriptions() {
  return _get(`${AUTHORING}/descriptions`);
}

export function getDescription(descId) {
  return _get(`${AUTHORING}/description/${descId}`);
}

// Step 2: Clarify
export function clarifyScenario(descId) {
  return _post(`${AUTHORING}/clarify/${descId}`);
}

export function getSummary(descId) {
  return _get(`${AUTHORING}/summary/${descId}`);
}

export function updateSummary(descId, updates) {
  return _put(`${AUTHORING}/summary/${descId}`, updates);
}

// Step 3: Questions & Answers
export function getQuestions(descId) {
  return _get(`${AUTHORING}/questions/${descId}`);
}

export function submitAnswers(descId, answers) {
  return _post(`${AUTHORING}/answers/${descId}`, { answers });
}

// Step 4: Generate
export function generateContract(descId) {
  return _post(`${AUTHORING}/generate/${descId}`);
}

export function getDraft(descId) {
  return _get(`${AUTHORING}/draft/${descId}`);
}

// Step 5: Validate
export function validateDraft(descId) {
  return _post(`${AUTHORING}/validate/${descId}`);
}

// Step 6: Map Events
export function mapEvents(descId, traceEvents) {
  return _post(`${AUTHORING}/map-events/${descId}`, { trace_events: traceEvents });
}

export function confirmEventMapping(descId, contractEvent, traceEvents) {
  return _post(`${AUTHORING}/confirm-mapping/${descId}`, {
    contract_event: contractEvent,
    trace_events: traceEvents,
  });
}

// Step 7: Lock
export function lockContract(descId) {
  return _post(`${AUTHORING}/lock/${descId}`);
}

export function getLockedContract(descId) {
  return _get(`${AUTHORING}/locked/${descId}`);
}
