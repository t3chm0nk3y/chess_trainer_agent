const API_BASE = import.meta.env.VITE_API_URL || "/api";

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

export function getGameMistakes(id) {
  return request(`/games/${id}/mistakes`);
}

export function getGameRecurring(id) {
  return request(`/games/${id}/recurring`);
}

export function importGames(maxGames = null) {
  const query = maxGames ? `?max_games=${maxGames}` : "";
  return request(`/games/import${query}`, { method: "POST" });
}

// --- Patterns ---
export function listPatterns(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/patterns?${query}`);
}

export function getPattern(id) {
  return request(`/patterns/${id}`);
}

export function getPatternReport() {
  return request("/patterns/report");
}

export function getConditions() {
  return request("/patterns/conditions");
}

// --- Openings ---
export function listOpenings(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/openings?${query}`);
}

export function getOpening(ecoCode) {
  return request(`/openings/${encodeURIComponent(ecoCode)}`);
}

export function computeOpenings() {
  return request("/openings/compute", { method: "POST" });
}

// --- Reports ---
export function listReports(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/reports?${query}`);
}

export function getReport(type, key) {
  return request(`/reports/${encodeURIComponent(type)}/${encodeURIComponent(key)}`);
}

export function generateReports() {
  return request("/reports/generate", { method: "POST" });
}

// --- Analysis ---
export function getAnalysisStatus() {
  return request("/analysis/status");
}

export function retryFailed() {
  return request("/analysis/retry-failed", { method: "POST" });
}
