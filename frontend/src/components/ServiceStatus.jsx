import { LINE_GROUPS, STATUS_TONES, timeLabel } from "../utils/alerts";
import LineBadge from "./LineBadge";

const PROBLEM_ORDER = ["Suspended", "Rerouted", "Delays"];

function LineRow({ item, onSelectLine }) {
  return (
    <li>
      <button type="button" className="status-row" onClick={() => onSelectLine(item.route)}>
        <LineBadge line={item.route} />
        <span className={`status-chip status-chip--${STATUS_TONES[item.status] || "muted"}`}>
          {item.status}
        </span>
        <span className="status-row__count">
          {item.alert_count > 0 ? `${item.alert_count} alert${item.alert_count === 1 ? "" : "s"}` : ""}
        </span>
        <span className="status-row__chevron" aria-hidden="true">›</span>
      </button>
    </li>
  );
}

export default function ServiceStatus({ state, onSelectLine, onReload, savedRoutes }) {
  const statuses = state.data ?? [];
  const byRoute = new Map(statuses.map((item) => [item.route, item]));
  const problems = statuses
    .filter((item) => PROBLEM_ORDER.includes(item.status))
    .sort((a, b) => PROBLEM_ORDER.indexOf(a.status) - PROBLEM_ORDER.indexOf(b.status));
  const updatedAt = statuses[0]?.updated_at;
  const stale = statuses.length > 0 && statuses[0].data_status !== "fresh";
  const saved = savedRoutes.map((route) => byRoute.get(route)).filter(Boolean);

  return (
    <section className="status-page" aria-labelledby="status-title">
      <div className="detail-hero status-hero">
        <span className="route-card__label">Live MTA data</span>
        <h1 id="status-title">Service status</h1>
        <p>
          {state.status === "loading" && "Loading line status…"}
          {updatedAt && <>MTA alerts updated {timeLabel(updatedAt)}</>}
          {state.loadedAt && <> · checked {timeLabel(state.loadedAt)}</>}
        </p>
        <button
          type="button"
          className="text-button text-button--small"
          onClick={onReload}
          disabled={state.status === "loading"}
        >
          Refresh
        </button>
      </div>

      {state.status === "error" && !state.data && (
        <div className="state-message state-message--error">
          <strong>Service status could not be loaded.</strong>
          <span>Make sure the backend is running, then try again.</span>
        </div>
      )}
      {stale && (
        <p className="station-section__message station-section__message--error">
          The MTA alert feed could not be refreshed, so line status is shown as Unknown.
        </p>
      )}

      {statuses.length > 0 && (
        <>
          <section className="station-section status-summary" aria-labelledby="status-now-title">
            <h2 id="status-now-title">Affecting riders now</h2>
            {problems.length === 0 ? (
              <p className="station-section__summary">
                No delays, reroutes or suspensions reported right now.
              </p>
            ) : (
              <div className="status-summary__groups">
                {PROBLEM_ORDER.map((status) => {
                  const lines = problems.filter((item) => item.status === status);
                  if (!lines.length) return null;
                  return (
                    <div className="status-summary__group" key={status}>
                      <span className={`status-chip status-chip--${STATUS_TONES[status]}`}>{status}</span>
                      <div className="status-summary__lines">
                        {lines.map((item) => (
                          <button
                            type="button"
                            key={item.route}
                            className="badge-button"
                            onClick={() => onSelectLine(item.route)}
                            aria-label={`${item.route} line details`}
                          >
                            <LineBadge line={item.route} />
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {saved.length > 0 && (
            <section className="station-section" aria-labelledby="status-saved-title">
              <h2 id="status-saved-title">Your lines</h2>
              <ul className="status-list">
                {saved.map((item) => (
                  <LineRow item={item} key={item.route} onSelectLine={onSelectLine} />
                ))}
              </ul>
            </section>
          )}

          <section className="station-section" aria-labelledby="status-all-title">
            <h2 id="status-all-title">All subway lines</h2>
            {LINE_GROUPS.map((group) => (
              <ul className="status-list" key={group.join("")}>
                {group
                  .map((route) => byRoute.get(route))
                  .filter(Boolean)
                  .map((item) => (
                    <LineRow item={item} key={item.route} onSelectLine={onSelectLine} />
                  ))}
              </ul>
            ))}
          </section>
        </>
      )}
    </section>
  );
}
