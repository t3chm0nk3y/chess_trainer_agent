const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// --- Games ---

export function listGames(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/games?${query}`);
}

export function getGame(id) {
  return request(`/games/${id}`);
}

export function getGameMoves(id) {
  return request(`/games/${id}/moves`);
}

export function deleteGame(id) {
  return request(`/games/${id}`, { method: "DELETE" });
}

export function uploadPGN(file) {
  const form = new FormData();
  form.append("file", file);
  return fetch(`${API_BASE}/games/upload`, { method: "POST", body: form }).then(
    (r) => r.json()
  );
}

export function importLichess(username, options = {}) {
  const params = new URLSearchParams({ username });
  if (options.since) params.set("since", options.since);
  if (options.color) params.set("color", options.color);
  if (options.rated !== null && options.rated !== undefined) params.set("rated", options.rated);
  if (options.time_control) params.set("time_control", options.time_control);
  return request(`/games/import/lichess?${params}`, { method: "POST" });
}

export function importChessCom(username, year, month) {
  const params = new URLSearchParams({ username });
  if (year) params.set("year", year);
  if (month) params.set("month", month);
  return request(`/games/import/chesscom?${params}`, { method: "POST" });
}

// --- Patterns ---

export function listPatterns() {
  return request("/patterns");
}

export function getPattern(id) {
  return request(`/patterns/${id}`);
}

export function refreshPatterns() {
  return request("/patterns/refresh", { method: "POST" });
}

// --- Analysis ---

export function compareGame(gameId) {
  return request("/analyze/compare", {
    method: "POST",
    body: JSON.stringify({ game_id: gameId }),
  });
}

export function getAnalysisStatus(jobId) {
  return request(`/analyze/status/${jobId}`);
}

// --- Progress ---

export function getProgress() {
  return request("/progress");
}

export function getProgressSummary() {
  return request("/progress/summary");
}

// --- Workflows ---

export function listWorkflows() {
  return request("/workflows");
}

export function getWorkflow(name) {
  return request(`/workflows/${name}`);
}

export function executeWorkflow(name, params = {}) {
  return request(`/workflows/${name}/execute`, {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function getWorkflowRunStatus(runId) {
  return request(`/workflows/runs/${runId}`);
}
