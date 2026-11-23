const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

async function request(path, { method = "GET", body, token, signal } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`);
    error.status = response.status;
    try {
      const payload = await response.json();
      error.detail = payload?.detail;
    } catch {
      // Error bodies are optional; the status code is enough to react to.
    }
    throw error;
  }
  // 204 responses have no body.
  return response.status === 204 ? null : response.json();
}

function fetchJson(path, { signal } = {}) {
  return request(path, { signal });
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

export function getServiceStatus(options) {
  return fetchJson("/status", options);
}

export function getAlerts({ stationId, route } = {}, options) {
  const params = new URLSearchParams();
  if (stationId) params.set("station_id", stationId);
  if (route) params.set("route", route);
  const query = params.toString();
  return fetchJson(`/alerts${query ? `?${query}` : ""}`, options);
}

export function getRouteReroutes(route, options) {
  return fetchJson(`/routes/${encodeURIComponent(route)}/reroutes`, options);
}

/** Plan a trip. `origin` / `destination` are { station_id } or { place_id }. */
export function planTrip(origin, destination, options) {
  return request("/trips/plan", {
    method: "POST",
    body: { origin, destination, departure_time: new Date().toISOString() },
    ...options,
  });
}

export function getPlaceSuggestions(query, options) {
  return fetchJson(
    `/places/autocomplete?query=${encodeURIComponent(query)}`,
    options,
  );
}

export function listFavorites(token) {
  return request("/me/favorites", { token });
}

export function saveFavorite(token, kind, targetId) {
  return request(
    `/me/favorites/${kind}/${encodeURIComponent(targetId)}`,
    { method: "PUT", token },
  );
}

export function deleteFavorite(token, kind, targetId) {
  return request(
    `/me/favorites/${kind}/${encodeURIComponent(targetId)}`,
    { method: "DELETE", token },
  );
}
