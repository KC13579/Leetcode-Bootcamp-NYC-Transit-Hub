import { useEffect, useMemo, useState } from "react";

import { getAlerts, getRouteReroutes } from "../api/client";
import {
  DISRUPTIONS,
  STATUS_TONES,
  causeLabel,
  cleanAlertText,
  dateTimeLabel,
  disruptionKind,
  timeLabel,
} from "../utils/alerts";
import FavoriteButton from "./FavoriteButton";
import LineBadge from "./LineBadge";

const STATUS_MEANING = {
  "Good Service": "No active problems are reported for this line.",
  Delays: "Trains are running, but expect longer waits and slower trips.",
  Rerouted: "Some trains run on a different path. Check which stops are skipped or added.",
  Suspended: "Part or all of this line is not running. Plan another route.",
  "Service Change": "Trains are running with planned changes. Read the notices before you ride.",
  Unknown: "Current status could not be confirmed from the MTA feed.",
};

function useResource(loader, key) {
  const [state, setState] = useState({ status: "loading", data: null });
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading", data: null });
    loader(key, { signal: controller.signal })
      .then((data) => setState({ status: "ready", data }))
      .catch((error) => {
        if (error.name !== "AbortError") setState({ status: "error", data: null, error });
      });
    return () => controller.abort();
  }, [loader, key]);
  return state;
}

const loadLineAlerts = (route, options) => getAlerts({ route }, options);

function StationLinks({ ids, stationsById, onOpenStation }) {
  return (
    <span className="station-link-list">
      {ids.map((id) => {
        const station = stationsById.get(id);
        return station ? (
          <button
            type="button"
            className="text-button text-button--small"
            key={id}
            onClick={() => onOpenStation(station)}
          >
            {station.name}
          </button>
        ) : null;
      })}
    </span>
  );
}

function AlertCard({ alert, route, stationsById, onOpenStation }) {
  const kind = disruptionKind(alert);
  const info = DISRUPTIONS[kind];
  const cause = causeLabel(alert.cause);
  const otherLines = alert.routes.filter((item) => item !== route);
  const knownStations = alert.station_ids.filter((id) => stationsById.has(id));

  return (
    <li className="line-alert">
      <div className="station-alert__top">
        <span className={`status-chip status-chip--${info.tone}`}>{info.label}</span>
        {alert.is_stale && <span className="status-chip status-chip--warn">May be outdated</span>}
      </div>
      <strong className="line-alert__title">{cleanAlertText(alert.title)}</strong>
      <dl className="line-alert__facts">
        <div>
          <dt>What it means</dt>
          <dd>{info.meaning}</dd>
        </div>
        {cause && (
          <div>
            <dt>Why</dt>
            <dd>{cause}</dd>
          </div>
        )}
        {knownStations.length > 0 && (
          <div>
            <dt>Stations</dt>
            <dd>
              <StationLinks ids={knownStations} stationsById={stationsById} onOpenStation={onOpenStation} />
            </dd>
          </div>
        )}
        {otherLines.length > 0 && (
          <div>
            <dt>Also affects</dt>
            <dd className="line-alert__lines">
              {otherLines.map((line) => (
                <LineBadge line={line} key={line} />
              ))}
            </dd>
          </div>
        )}
        {(alert.starts_at || alert.ends_at) && (
          <div>
            <dt>When</dt>
            <dd>
              {alert.starts_at && <>From {dateTimeLabel(alert.starts_at)}</>}
              {alert.starts_at && alert.ends_at && " "}
              {alert.ends_at && <>until {dateTimeLabel(alert.ends_at)}</>}
            </dd>
          </div>
        )}
      </dl>
      {alert.description && (
        <details>
          <summary>Full MTA notice</summary>
          <p>{cleanAlertText(alert.description)}</p>
        </details>
      )}
    </li>
  );
}

function RerouteSection({ route, stationsById, onOpenStation }) {
  const reroutes = useResource(getRouteReroutes, route);
  const patterns = (reroutes.data ?? []).filter(
    (item) => item.skipped_station_ids?.length || item.added_station_ids?.length,
  );

  // Merge trips that skip/add the same stations so riders see one entry per pattern.
  const merged = useMemo(() => {
    const groups = new Map();
    patterns.forEach((item) => {
      const key = `${item.direction}|${item.skipped_station_ids?.join()}|${item.added_station_ids?.join()}`;
      if (!groups.has(key)) groups.set(key, { ...item, trips: 0 });
      groups.get(key).trips += 1;
    });
    return Array.from(groups.values());
  }, [patterns]);

  return (
    <section className="station-section" aria-labelledby="reroute-title">
      <div className="station-section__heading">
        <h2 id="reroute-title">Reroutes &amp; skipped stops</h2>
      </div>
      <p className="station-section__note">
        Compares trains running now with the published schedule.
      </p>
      {reroutes.status === "loading" && (
        <p className="station-section__message station-section__message--muted">Checking live trains…</p>
      )}
      {reroutes.status === "error" && (
        <p className="station-section__message station-section__message--error">
          Live reroute data could not be loaded.
        </p>
      )}
      {reroutes.status === "ready" && merged.length === 0 && (
        <p className="station-section__summary">
          No running {route} trains show skipped or added stops compared with the schedule.
        </p>
      )}
      {merged.length > 0 && (
        <ul className="reroute-list">
          {merged.map((item) => (
            <li className="reroute-item" key={`${item.direction}-${item.trip_id}`}>
              <div className="reroute-item__top">
                <strong>
                  {item.direction === "0" ? "Northbound" : item.direction === "1" ? "Southbound" : "Trains"}
                </strong>
                <span>
                  {item.trips} train{item.trips === 1 ? "" : "s"}
                  {item.updated_at && <> · {timeLabel(item.updated_at)}</>}
                </span>
              </div>
              {item.skipped_station_ids?.length > 0 && (
                <p>
                  <span className="status-chip status-chip--bad">Skips</span>{" "}
                  <StationLinks ids={item.skipped_station_ids} stationsById={stationsById} onOpenStation={onOpenStation} />
                </p>
              )}
              {item.added_station_ids?.length > 0 && (
                <p>
                  <span className="status-chip status-chip--good">Adds</span>{" "}
                  <StationLinks ids={item.added_station_ids} stationsById={stationsById} onOpenStation={onOpenStation} />
                </p>
              )}
              {item.evidence_status !== "confirmed" && (
                <p className="equipment-item__detail">Partial data: some stops could not be confirmed.</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Line page: current status, rider-friendly alert explanations and reroute evidence. */
export default function LineDetails({ route, statusItem, stations, onBack, onOpenStation }) {
  const alerts = useResource(loadLineAlerts, route);
  const stationsById = useMemo(
    () => new Map(stations.map((station) => [station.id, station])),
    [stations],
  );
  const status = statusItem?.status ?? "Unknown";
  const items = alerts.data ?? [];
  const order = ["suspension", "reroute", "delay", "skip", "service_change", "other"];
  const sorted = [...items].sort(
    (a, b) => order.indexOf(disruptionKind(a)) - order.indexOf(disruptionKind(b)),
  );

  return (
    <section className="line-details" aria-labelledby="line-title">
      <div className="detail-actions">
        <button type="button" className="text-button" onClick={onBack}>
          <span aria-hidden="true">←</span> Service status
        </button>
        <FavoriteButton kind="route" targetId={route} label={`${route} line`} />
      </div>

      <div className="detail-card">
        <div className="detail-hero line-hero">
          <span className="line-hero__badge">
            <LineBadge line={route} />
          </span>
          <div>
            <h1 id="line-title">{route} line</h1>
            <span className={`status-chip status-chip--${STATUS_TONES[status] || "muted"}`}>{status}</span>
            <p>{STATUS_MEANING[status] ?? STATUS_MEANING.Unknown}</p>
          </div>
        </div>

        <section className="station-section" aria-labelledby="line-alerts-title">
          <div className="station-section__heading">
            <h2 id="line-alerts-title">What's happening</h2>
            {alerts.data && <span className="station-section__count">{items.length}</span>}
          </div>
          {alerts.status === "loading" && (
            <p className="station-section__message station-section__message--muted">Loading alerts…</p>
          )}
          {alerts.status === "error" && (
            <p className="station-section__message station-section__message--error">
              Alerts could not be loaded.
            </p>
          )}
          {alerts.status === "ready" && items.length === 0 && (
            <p className="station-section__summary">No active alerts for the {route} line.</p>
          )}
          {sorted.length > 0 && (
            <ul className="station-alerts">
              {sorted.map((alert) => (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  route={route}
                  stationsById={stationsById}
                  onOpenStation={onOpenStation}
                />
              ))}
            </ul>
          )}
        </section>

        <RerouteSection route={route} stationsById={stationsById} onOpenStation={onOpenStation} />
      </div>
    </section>
  );
}
