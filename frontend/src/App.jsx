import { useEffect, useMemo, useState } from "react";
import {
  getAlerts,
  getServiceStatus,
  getStationArrivals,
  getStations,
} from "./api/client";

function formatTime(isoString) {
  if (!isoString) return "—";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  return date.toLocaleString();
}

export default function App() {
  const [stations, setStations] = useState([]);
  const [stationsLoading, setStationsLoading] = useState(true);
  const [stationsError, setStationsError] = useState(false);

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStationId, setSelectedStationId] = useState("");

  const [arrivals, setArrivals] = useState([]);
  const [arrivalsLoading, setArrivalsLoading] = useState(false);
  const [arrivalsError, setArrivalsError] = useState(false);

  const [statuses, setStatuses] = useState([]);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState(false);

  const [alerts, setAlerts] = useState([]);
  const [alertsLoading, setAlertsLoading] = useState(true);
  const [alertsError, setAlertsError] = useState(false);

  const [lastUpdated, setLastUpdated] = useState(null);

  const stationById = useMemo(() => {
    const map = {};
    for (const station of stations) {
      map[station.id] = station;
    }
    return map;
  }, [stations]);

  const filteredStations = useMemo(() => {
    const term = searchQuery.trim().toLowerCase();
    if (!term) return stations;
    return stations.filter((station) =>
      station.name.toLowerCase().includes(term)
    );
  }, [stations, searchQuery]);

  const selectedStation = stationById[selectedStationId] || null;

  async function loadStations() {
    setStationsLoading(true);
    setStationsError(false);
    try {
      const data = await getStations();
      setStations(data);
      if (data.length > 0 && !selectedStationId) {
        setSelectedStationId(data[0].id);
      }
      setLastUpdated(new Date());
    } catch {
      setStationsError(true);
    } finally {
      setStationsLoading(false);
    }
  }

  async function loadArrivals(stationId) {
    if (!stationId) {
      setArrivals([]);
      return;
    }
    setArrivalsLoading(true);
    setArrivalsError(false);
    try {
      const data = await getStationArrivals(stationId);
      setArrivals(data);
      setLastUpdated(new Date());
    } catch {
      setArrivalsError(true);
    } finally {
      setArrivalsLoading(false);
    }
  }

  async function loadStatusAndAlerts() {
    setStatusLoading(true);
    setStatusError(false);
    setAlertsLoading(true);
    setAlertsError(false);

    const [statusResult, alertsResult] = await Promise.allSettled([
      getServiceStatus(),
      getAlerts(),
    ]);

    let anySuccess = false;

    if (statusResult.status === "fulfilled") {
      setStatuses(statusResult.value);
      anySuccess = true;
    } else {
      setStatusError(true);
    }
    setStatusLoading(false);

    if (alertsResult.status === "fulfilled") {
      setAlerts(alertsResult.value);
      anySuccess = true;
    } else {
      setAlertsError(true);
    }
    setAlertsLoading(false);

    if (anySuccess) {
      setLastUpdated(new Date());
    }
  }

  function handleRefresh() {
    if (selectedStationId) {
      loadArrivals(selectedStationId);
    }
    loadStatusAndAlerts();
  }

  useEffect(() => {
    loadStations();
    loadStatusAndAlerts();
  }, []);

  useEffect(() => {
    if (selectedStationId) {
      loadArrivals(selectedStationId);
    }
  }, [selectedStationId]);

  return (
    <div className="container">
      <header className="page-header">
        <div>
          <h1>NYC Transit Hub</h1>
          <p className="subtitle">
            Last updated: {lastUpdated ? lastUpdated.toLocaleTimeString() : "—"}
          </p>
        </div>
        <button type="button" onClick={handleRefresh}>
          Refresh Data
        </button>
      </header>

      {/* 1. Station selector */}
      <section className="section">
        <h2>1. Station Selector</h2>
        {stationsLoading && <p>Loading...</p>}
        {stationsError && <p className="error">Failed to load data</p>}
        {!stationsLoading && !stationsError && stations.length === 0 && (
          <p>No data available</p>
        )}
        {!stationsLoading && !stationsError && stations.length > 0 && (
          <div className="selector-controls">
            <label htmlFor="station-search">
              Search by station name:
              <input
                id="station-search"
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="e.g. Times Sq, Astoria, 34 St..."
              />
            </label>

            <label htmlFor="station-select">
              Select station ({filteredStations.length} matches):
              <select
                id="station-select"
                value={selectedStationId}
                onChange={(e) => setSelectedStationId(e.target.value)}
              >
                {filteredStations.length === 0 && (
                  <option value="">No matching stations</option>
                )}
                {filteredStations.map((station) => (
                  <option key={station.id} value={station.id}>
                    {station.name} ({station.routes.join(", ")}) — [{station.id}]
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
      </section>

      {/* 2. Station information */}
      <section className="section">
        <h2>2. Station Information</h2>
        {!selectedStation ? (
          <p>No data available</p>
        ) : (
          <dl className="info-grid">
            <div>
              <dt>Canonical ID</dt>
              <dd>
                <code>{selectedStation.id}</code>
              </dd>
            </div>
            <div>
              <dt>Name</dt>
              <dd>{selectedStation.name}</dd>
            </div>
            <div>
              <dt>Subway Routes</dt>
              <dd>
                {selectedStation.routes.length > 0
                  ? selectedStation.routes.join(", ")
                  : "None"}
              </dd>
            </div>
            <div>
              <dt>Borough</dt>
              <dd>{selectedStation.borough || "—"}</dd>
            </div>
            <div>
              <dt>Latitude / Longitude</dt>
              <dd>
                {selectedStation.latitude}, {selectedStation.longitude}
              </dd>
            </div>
            <div>
              <dt>Stop IDs</dt>
              <dd>{selectedStation.stop_ids.join(", ")}</dd>
            </div>
          </dl>
        )}
      </section>

      {/* 3. Live arrivals */}
      <section className="section">
        <h2>
          3. Live Arrivals
          {selectedStation ? ` — ${selectedStation.name}` : ""}
        </h2>
        {arrivalsLoading && <p>Loading...</p>}
        {arrivalsError && <p className="error">Failed to load data</p>}
        {!arrivalsLoading && !arrivalsError && arrivals.length === 0 && (
          <p>No data available</p>
        )}
        {!arrivalsLoading && !arrivalsError && arrivals.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Route</th>
                <th>Direction</th>
                <th>Destination</th>
                <th>Minutes Away</th>
                <th>Arrival Time</th>
              </tr>
            </thead>
            <tbody>
              {arrivals.map((arrival) => (
                <tr key={`${arrival.trip_id}-${arrival.arrival_time}`}>
                  <td>
                    <strong>{arrival.route}</strong>
                  </td>
                  <td>{arrival.direction}</td>
                  <td>{arrival.destination || "—"}</td>
                  <td>
                    {arrival.minutes_away === 0
                      ? "Due"
                      : `${arrival.minutes_away} min`}
                  </td>
                  <td>{formatTime(arrival.arrival_time)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* 4. Service status */}
      <section className="section">
        <h2>4. Service Status</h2>
        {statusLoading && <p>Loading...</p>}
        {statusError && <p className="error">Failed to load data</p>}
        {!statusLoading && !statusError && statuses.length === 0 && (
          <p>No data available</p>
        )}
        {!statusLoading && !statusError && statuses.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Route</th>
                <th>Status</th>
                <th>Active Alerts</th>
              </tr>
            </thead>
            <tbody>
              {statuses.map((item) => (
                <tr key={item.route}>
                  <td>
                    <strong>{item.route}</strong>
                  </td>
                  <td>{item.status}</td>
                  <td>{item.alert_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* 5. Active alerts */}
      <section className="section">
        <h2>5. Active Alerts</h2>
        {alertsLoading && <p>Loading...</p>}
        {alertsError && <p className="error">Failed to load data</p>}
        {!alertsLoading && !alertsError && alerts.length === 0 && (
          <p>No data available</p>
        )}
        {!alertsLoading && !alertsError && alerts.length > 0 && (
          <ul className="alerts-list">
            {alerts.map((alert) => {
              const stationLabels = alert.station_ids.map((id) =>
                stationById[id] ? `${stationById[id].name} (${id})` : id
              );
              return (
                <li key={alert.id} className="alert-item">
                  <h3>{alert.title}</h3>
                  {alert.description && (
                    <p className="alert-description">{alert.description}</p>
                  )}
                  <p>
                    <strong>Affected route(s):</strong>{" "}
                    {alert.routes.length > 0 ? alert.routes.join(", ") : "None"}
                  </p>
                  {stationLabels.length > 0 && (
                    <p>
                      <strong>Affected station(s):</strong>{" "}
                      {stationLabels.join(", ")}
                    </p>
                  )}
                  {(alert.starts_at || alert.ends_at) && (
                    <p>
                      <strong>Time:</strong> Start: {formatTime(alert.starts_at)}{" "}
                      | End: {formatTime(alert.ends_at)}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
