const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

async function fetchJson(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

export function getStations() {
  return fetchJson("/stations?limit=500");
}

export function getStationArrivals(stationId) {
  return fetchJson(
    `/stations/${encodeURIComponent(stationId)}/arrivals?limit=20`
  );
}

export function getServiceStatus() {
  return fetchJson("/status");
}

export function getAlerts() {
  return fetchJson("/alerts");
}
