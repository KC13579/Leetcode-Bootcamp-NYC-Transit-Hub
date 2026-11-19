const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

async function fetchJson(path, { signal } = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, { signal });
  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

export function getStations() {
  return fetchJson("/stations?limit=500");
}

export function getMapNetwork() {
  return fetchJson("/map/lines");
}

export function getStation(stationId, options) {
  return fetchJson(`/stations/${encodeURIComponent(stationId)}`, options);
}

export function getStationArrivals(stationId, options) {
  return fetchJson(
    `/stations/${encodeURIComponent(stationId)}/arrivals?limit=20`,
    options,
  );
}

export function getStationAccessibility(stationId, options) {
  return fetchJson(
    `/stations/${encodeURIComponent(stationId)}/accessibility`,
    options,
  );
}

export function getServiceStatus() {
  return fetchJson("/status");
}

export function getAlerts({ stationId, route } = {}, options) {
  const params = new URLSearchParams();
  if (stationId) params.set("station_id", stationId);
  if (route) params.set("route", route);
  const query = params.toString();
  return fetchJson(`/alerts${query ? `?${query}` : ""}`, options);
}
