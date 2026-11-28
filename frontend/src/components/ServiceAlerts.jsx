import { useEffect, useState } from "react";
import { getAlerts } from "../api/client";
import "./ServiceAlerts.css";

const routeColors = {
  "1": "#EE352E",
  "2": "#EE352E",
  "3": "#EE352E",
  "4": "#00933C",
  "5": "#00933C",
  "6": "#00933C",
  "7": "#B933AD",
  A: "#0039A6",
  C: "#0039A6",
  E: "#0039A6",
  B: "#FF6319",
  D: "#FF6319",
  F: "#FF6319",
  M: "#FF6319",
  N: "#FCCC0A",
  Q: "#FCCC0A",
  R: "#FCCC0A",
  W: "#FCCC0A",
  G: "#6CBE45",
  J: "#996633",
  Z: "#996633",
  L: "#A7A9AC",
  S: "#808183",
};

export default function ServiceAlerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;

    async function loadAlerts() {
      try {
        const data = await getAlerts();

        if (!Array.isArray(data)) {
          throw new Error("Invalid alert data");
        }

        if (active) {
          setAlerts(data);
          setError(false);
          setLastUpdated(new Date());
        }
      } catch {
        if (active) {
          setError(true);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadAlerts();

    const timer = setInterval(loadAlerts, 60000);

    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [refreshKey]);

  function refreshAlerts() {
    setLoading(true);
    setRefreshKey((key) => key + 1);
  }

  return (
    <section className="service-alerts">
      <button
        type="button"
        className="service-alerts-toggle"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <span>🔔 Service Alerts</span>

        <span className="service-alerts-count">
          {loading
            ? "Loading..."
            : error
            ? "Unavailable"
            : `${alerts.length} alerts`}
        </span>

        <span>{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div className="service-alerts-content">
          <div className="service-alerts-toolbar">
            <span>
              {lastUpdated
                ? `Updated: ${lastUpdated.toLocaleTimeString()}`
                : "NYC Subway Status"}
            </span>

            <button
              type="button"
              onClick={refreshAlerts}
              disabled={loading}
            >
              ↻ Refresh
            </button>
          </div>

          {loading && <p>Loading service alerts...</p>}

          {error && (
            <p className="service-alerts-error">
              Unable to load service alerts.
              Please try again.
            </p>
          )}

          {!loading && !error && alerts.length === 0 && (
            <p className="service-alerts-empty">
              No active alerts reported.
            </p>
          )}

          {!loading &&
            !error &&
            alerts.map((alert, index) => (
              <article
                className="service-alerts-item"
                key={alert.id ?? index}
              >
                <div className="service-alerts-routes">
                  {(alert.routes || []).map((route) => (
                    <span
                      key={route}
                      className="service-alerts-route"
                      style={{
                        backgroundColor:
                          routeColors[route] || "#666",
                        color: ["N", "Q", "R", "W"].includes(route)
                          ? "#111"
                          : "#fff",
                      }}
                    >
                      {route}
                    </span>
                  ))}
                </div>

                <h4>
                  {alert.title ||
                    alert.header ||
                    alert.header_text ||
                    "Service Alert"}
                </h4>

                <p>
                  {alert.description ||
                    alert.description_text ||
                    alert.message ||
                    "No additional details available."}
                </p>
              </article>
            ))}
        </div>
      )}
    </section>
  );
}