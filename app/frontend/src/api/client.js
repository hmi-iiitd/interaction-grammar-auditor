const API_BASE = 'http://localhost:8000/api';

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
