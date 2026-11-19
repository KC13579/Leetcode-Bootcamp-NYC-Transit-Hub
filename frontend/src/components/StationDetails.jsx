import { useCallback, useEffect, useState } from "react";

import {
  getAlerts,
  getStation,
  getStationAccessibility,
  getStationArrivals,
} from "../api/client";
import LineBadge from "./LineBadge";

const ARRIVALS_REFRESH_MS = 30_000;
const MAX_TIMES_PER_ROUTE = 3;
// Borough codes used in MTA's static station data.
const BOROUGHS = { M: "Manhattan", Bk: "Brooklyn", Bx: "Bronx", Q: "Queens", SI: "Staten Island" };

function timeLabel(value) {
  if (!value) return null;
  return new Date(value).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

function dateTimeLabel(value) {
  if (!value) return null;
  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/**
 * Load one backend resource for a station. Each section of the page uses its
 * own instance so one failing feed does not blank the whole page.
 */
function useStationResource(loader, stationId, refreshMs) {
  const [state, setState] = useState({ status: "loading", data: null, error: null });
  const [loadedAt, setLoadedAt] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setState((previous) =>
      previous.data ? { ...previous, status: "refreshing" } : { status: "loading", data: null, error: null },
    );
    loader(stationId, { signal: controller.signal })
      .then((data) => {
        setState({ status: "ready", data, error: null });
        setLoadedAt(new Date());
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        // Keep the last good data visible if a background refresh fails.
        setState((previous) => ({ status: "error", data: previous.data, error }));
      });
    return () => controller.abort();
  }, [loader, stationId, reloadKey]);

  useEffect(() => {
    if (!refreshMs) return undefined;
    const timer = setInterval(reload, refreshMs);
    return () => clearInterval(timer);
  }, [refreshMs, reload]);

  return { ...state, loadedAt, reload };
}

const loadAlerts = (stationId, options) => getAlerts({ stationId }, options);

function SectionMessage({ children, tone = "muted" }) {
  return <p className={`station-section__message station-section__message--${tone}`}>{children}</p>;
}

function groupArrivals(arrivals) {
  const directions = new Map();
  arrivals.forEach((arrival) => {
    if (!directions.has(arrival.direction)) {
      directions.set(arrival.direction, {
        direction: arrival.direction,
        destination: arrival.destination,
        routes: new Map(),
      });
    }
    const group = directions.get(arrival.direction);
    if (!group.routes.has(arrival.route)) group.routes.set(arrival.route, []);
    group.routes.get(arrival.route).push(arrival);
  });
  return Array.from(directions.values());
}

function ArrivalsSection({ stationId }) {
  const arrivals = useStationResource(getStationArrivals, stationId, ARRIVALS_REFRESH_MS);
  const groups = arrivals.data ? groupArrivals(arrivals.data) : [];

  return (
    <section className="station-section" aria-labelledby="station-arrivals-title">
      <div className="station-section__heading">
        <h2 id="station-arrivals-title">Upcoming trains</h2>
        <div className="station-section__meta">
          {arrivals.loadedAt && <span>Updated {timeLabel(arrivals.loadedAt)}</span>}
          <button
            type="button"
            className="text-button text-button--small"
            onClick={arrivals.reload}
            disabled={arrivals.status === "loading" || arrivals.status === "refreshing"}
          >
            Refresh
          </button>
        </div>
      </div>

      {arrivals.status === "loading" && <SectionMessage>Loading arrivals…</SectionMessage>}
      {arrivals.status === "error" && (
        <SectionMessage tone="error">
          {arrivals.data
            ? "Could not refresh arrivals. Showing the last update."
            : "Arrivals could not be loaded right now."}
        </SectionMessage>
      )}
      {arrivals.data && groups.length === 0 && (
        <SectionMessage>No trains predicted in the next two hours.</SectionMessage>
      )}

      {groups.length > 0 && (
        <div className="arrival-groups">
          {groups.map((group) => (
            <div className="arrival-group" key={group.direction}>
              <h3>
                {group.direction}
                {group.destination && <span> · {group.destination}</span>}
              </h3>
              <ul>
                {Array.from(group.routes.entries()).map(([route, items]) => (
                  <li className="arrival-row" key={route}>
                    <LineBadge line={route} />
                    <span className="arrival-row__times">
                      {items.slice(0, MAX_TIMES_PER_ROUTE).map((item, index) => (
                        <time
                          key={item.trip_id}
                          dateTime={item.arrival_time}
                          title={timeLabel(item.arrival_time)}
                          className={index === 0 ? "arrival-row__next" : undefined}
                        >
                          {item.minutes_away === 0 ? "Now" : `${item.minutes_away} min`}
                        </time>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function adaLabel(accessible, adaStatus) {
  if (accessible === null) {
    if (adaStatus === "full") accessible = true;
    if (adaStatus === "none") accessible = false;
  }
  if (accessible === true) return { text: "ADA accessible station", tone: "good" };
  if (accessible === false) return { text: "Not ADA accessible", tone: "bad" };
  if (adaStatus === "partial") return { text: "Partially ADA accessible", tone: "warn" };
  return { text: "ADA status unknown", tone: "muted" };
}

function EquipmentStatus({ item }) {
  if (item.status === "out_of_service") {
    return <span className="status-chip status-chip--bad">Out of service</span>;
  }
  if (item.status === "operational") {
    return <span className="status-chip status-chip--good">Working</span>;
  }
  if (item.upcoming) {
    return <span className="status-chip status-chip--warn">Planned outage</span>;
  }
  return <span className="status-chip status-chip--muted">No reported outage</span>;
}

function AccessibilitySection({ stationId, adaStatus }) {
  const accessibility = useStationResource(getStationAccessibility, stationId);
  const data = accessibility.data;
  const ada = adaLabel(data?.accessible ?? null, adaStatus);
  const equipment = data?.equipment ?? [];
  const outages = equipment.filter((item) => item.status === "out_of_service").length;

  return (
    <section className="station-section" aria-labelledby="station-access-title">
      <div className="station-section__heading">
        <h2 id="station-access-title">Accessibility</h2>
        {(data || adaStatus) && (
          <span className={`status-chip status-chip--${ada.tone}`}>{ada.text}</span>
        )}
      </div>

      {accessibility.status === "loading" && (
        <SectionMessage>Loading elevators and escalators…</SectionMessage>
      )}
      {accessibility.status === "error" && !data && (
        <SectionMessage tone="error">
          {accessibility.error?.status === 503
            ? "Accessibility data is not available from the server."
            : "Elevator and escalator status could not be loaded."}
        </SectionMessage>
      )}

      {data && equipment.length === 0 && (
        <SectionMessage>No elevators or escalators are listed for this station.</SectionMessage>
      )}

      {equipment.length > 0 && (
        <>
          <p className="station-section__summary">
            {outages === 0
              ? `${equipment.length} elevator/escalator${equipment.length === 1 ? "" : "s"} listed, none reported out of service.`
              : `${outages} of ${equipment.length} reported out of service.`}
          </p>
          <ul className="equipment-list">
            {equipment.map((item) => (
              <li
                className={`equipment-item${item.status === "out_of_service" ? " equipment-item--outage" : ""}`}
                key={item.equipment_id}
              >
                <div className="equipment-item__top">
                  <strong>
                    {item.kind === "elevator" ? "Elevator" : "Escalator"} {item.equipment_id}
                  </strong>
                  <EquipmentStatus item={item} />
                </div>
                {item.location && <p>{item.location}</p>}
                {item.reason && <p className="equipment-item__detail">Reason: {item.reason}</p>}
                {item.upcoming && item.outage_start && (
                  <p className="equipment-item__detail">Starts {dateTimeLabel(item.outage_start)}</p>
                )}
                {item.expected_restore_at && (
                  <p className="equipment-item__detail">
                    Expected back {dateTimeLabel(item.expected_restore_at)}
                  </p>
                )}
                {item.status === "out_of_service" && item.alternative_route && (
                  <p className="equipment-item__detail">Alternative: {item.alternative_route}</p>
                )}
              </li>
            ))}
          </ul>
        </>
      )}

      {data?.note && <p className="station-section__note">{data.note}</p>}
    </section>
  );
}

function AlertsSection({ stationId }) {
  const alerts = useStationResource(loadAlerts, stationId);
  const items = alerts.data ?? [];

  return (
    <section className="station-section" aria-labelledby="station-alerts-title">
      <div className="station-section__heading">
        <h2 id="station-alerts-title">Service alerts</h2>
        {alerts.data && <span className="station-section__count">{items.length}</span>}
      </div>

      {alerts.status === "loading" && <SectionMessage>Loading alerts…</SectionMessage>}
      {alerts.status === "error" && !alerts.data && (
        <SectionMessage tone="error">Service alerts could not be loaded.</SectionMessage>
      )}
      {alerts.data && items.length === 0 && (
        <SectionMessage>No active alerts for this station or its lines.</SectionMessage>
      )}

      {items.length > 0 && (
        <ul className="station-alerts">
          {items.map((alert) => (
            <li className="station-alert" key={alert.id}>
              <div className="station-alert__top">
                <div className="station-alert__lines">
                  {alert.routes.map((route) => (
                    <LineBadge line={route} key={route} />
                  ))}
                </div>
                {alert.is_stale && (
                  <span className="status-chip status-chip--warn">May be outdated</span>
                )}
              </div>
              <strong>{alert.title}</strong>
              {alert.description && (
                <details>
                  <summary>Details</summary>
                  <p>{alert.description}</p>
                </details>
              )}
              {(alert.starts_at || alert.ends_at) && (
                <p className="station-alert__window">
                  {alert.starts_at && <>From {dateTimeLabel(alert.starts_at)}</>}
                  {alert.starts_at && alert.ends_at && " "}
                  {alert.ends_at && <>until {dateTimeLabel(alert.ends_at)}</>}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/**
 * Station page: lines, live arrivals, elevator/escalator status and alerts.
 * `station` is the summary object from /stations (id, name, routes); the full
 * record is fetched from /stations/{id} for borough and ADA status.
 */
export default function StationDetails({ station, onBack }) {
  const details = useStationResource(getStation, station.id);
  const full = details.data ?? station;

  return (
    <section className="station-details" aria-labelledby="station-details-title">
      <div className="detail-actions">
        <button type="button" className="text-button" onClick={onBack}>
          <span aria-hidden="true">←</span> Back
        </button>
      </div>

      <div className="detail-card">
        <div className="detail-hero">
          <span className="route-card__label">Station</span>
          <h1 id="station-details-title">{full.name}</h1>
          {full.borough && <p>{BOROUGHS[full.borough] ?? full.borough}</p>}
          <div className="station-details__lines">
            {full.routes.map((route) => (
              <LineBadge line={route} key={route} />
            ))}
          </div>
        </div>

        <ArrivalsSection stationId={station.id} />
        <AccessibilitySection stationId={station.id} adaStatus={details.data?.ada_status} />
        <AlertsSection stationId={station.id} />
      </div>
    </section>
  );
}
