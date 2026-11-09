import { lineColor } from "../data/mockTrips";
import LineBadge from "./LineBadge";
import TransitIcon from "./TransitIcon";

function timeLabel(value) {
  return new Date(value).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

function StepMarker({ step }) {
  if (step.type === "subway") {
    return <LineBadge line={step.line} />;
  }
  return (
    <span className={`step-marker step-marker--${step.type}`} aria-hidden="true">
      <TransitIcon type="walk" size={15} />
    </span>
  );
}

export default function TripDetails({ trip, onBack, onEdit }) {
  return (
    <section className="trip-details" aria-labelledby="trip-details-title">
      <div className="detail-actions">
        <button type="button" className="text-button" onClick={onBack}>
          <span aria-hidden="true">←</span> Route options
        </button>
        <button
          type="button"
          className="button button--quiet button--compact"
          onClick={onEdit}
        >
          Edit
        </button>
      </div>

      <div className="detail-card">
        <div className="detail-hero">
          <span className="route-card__label">{trip.label}</span>
          <h1 id="trip-details-title">{trip.duration} min</h1>
          <p>{trip.origin.name} <span aria-hidden="true">→</span> {trip.destination.name}</p>
        </div>

        <div className="itinerary-card">
          <div className="itinerary-card__heading">
            <div className="itinerary-card__lines">
              {trip.lines.map((line) => <LineBadge line={line} key={line} />)}
            </div>
          </div>

          <ol className="timeline">
            {trip.steps.map((step, index) => (
              <li
                className={`timeline__step timeline__step--${step.type}`}
                key={`${step.type}-${step.title}`}
                style={{
                  "--step-color":
                    step.type === "subway" ? lineColor(step.line) : "#344451",
                }}
              >
                <div className="timeline__rail">
                  <StepMarker step={step} />
                  {index < trip.steps.length - 1 && (
                    <span className="timeline__connector" aria-hidden="true" />
                  )}
                </div>
                <div className="timeline__content">
                  {step.type === "walk" && (
                    <div className="timeline__compact-step">
                      <strong>
                        Walk {step.duration} min ({step.distance})
                      </strong>
                      {index === 0 && (
                        <time>{timeLabel(trip.departureTime)}</time>
                      )}
                      {index === trip.steps.length - 1 && (
                        <time>{timeLabel(trip.arrivalTime)}</time>
                      )}
                    </div>
                  )}

                  {step.type === "subway" && (
                    <div
                      className="timeline__segment"
                      style={{ "--line-color": lineColor(step.line) }}
                    >
                      <div className="timeline__segment-heading">
                        <h3>{step.stops[0]}</h3>
                        <strong>{step.duration} min</strong>
                      </div>
                      <p className="timeline__direction">
                        Follow signs for {step.direction} · {step.line} platform
                      </p>
                      <details className="stop-list">
                        <summary>
                          Ride {step.stops.length - 1} stops
                        </summary>
                        <ol>
                          {step.stops.slice(1, -1).map((stop) => (
                            <li key={stop}>{stop}</li>
                          ))}
                        </ol>
                      </details>
                      <div className="timeline__arrival-stop">
                        <span aria-hidden="true" />
                        <strong>{step.stops[step.stops.length - 1]}</strong>
                      </div>
                    </div>
                  )}

                  {step.type === "transfer" && (
                    <div className="timeline__transfer">
                      <strong>Walk {step.duration} min</strong>
                      <span>Wait {step.waitDuration} min</span>
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>

      {trip.alerts.length > 0 && (
        <div className="trip-alerts">
          <h2>Service alerts</h2>
          {trip.alerts.map((alert) => (
            <article key={alert.id}>
              <div>
                <span aria-hidden="true">!</span>
                <strong>{alert.routes.filter((route) => trip.lines.includes(route)).join(", ")}</strong>
              </div>
              <p>{alert.title}</p>
              {alert.description && <p>{alert.description}</p>}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
