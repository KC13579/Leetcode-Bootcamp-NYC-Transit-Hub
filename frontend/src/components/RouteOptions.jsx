import { lineColor, lineUsesDarkText } from "../data/mockTrips";
import TransitIcon from "./TransitIcon";

function timeLabel(value) {
  return new Date(value).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function RouteOptions({ origin, destination, trips, onSelect, onModify }) {
  return (
    <section className="trip-results" aria-labelledby="route-options-title">
      <div className="trip-summary">
        <div>
          <h1 id="route-options-title">Choose a route</h1>
          <p>{origin.name} <span aria-hidden="true">→</span> {destination.name}</p>
        </div>
        <button
          type="button"
          className="button button--quiet button--compact"
          onClick={onModify}
        >
          Edit
        </button>
      </div>

      <div className="route-options">
        {trips.map((trip) => (
          <button
            type="button"
            className="route-card"
            key={trip.id}
            onClick={() => onSelect(trip)}
          >
            <div className="route-card__top">
              <div className="route-card__duration">
                <strong>{trip.duration} min</strong>
                <span>
                  {timeLabel(trip.departureTime)} – {timeLabel(trip.arrivalTime)}
                </span>
              </div>
              <div className="route-card__meta">
                <span className="route-card__label">{trip.label}</span>
                <span className="icon-time">
                  <TransitIcon type="walk" size={15} />
                  {trip.walking} min
                </span>
              </div>
            </div>

            <div className="route-preview" aria-label="Route preview">
              {trip.steps
                .filter((step) => step.type !== "transfer")
                .map((step) => {
                  const backgroundColor =
                    step.type === "subway" ? lineColor(step.line) : "#344451";
                  const darkText =
                    step.type === "subway" && lineUsesDarkText(step.line);
                  return (
                  <span
                    className={`route-preview__segment route-preview__segment--${step.type}`}
                    key={`${step.type}-${step.title}`}
                    style={{
                      backgroundColor,
                      color: darkText ? "#171717" : "#FFFFFF",
                      flexGrow: Math.max(step.duration, 5),
                    }}
                  >
                    <TransitIcon
                      type={step.type === "subway" ? "train" : "walk"}
                      size={14}
                    />
                    {step.type === "subway" && <strong>{step.line}</strong>}
                    <span>{step.duration}m</span>
                  </span>
                );
                })}
            </div>

            {trip.alerts.length > 0 && (
              <div className="route-alert">
                <span aria-hidden="true">!</span>
                Alert for {trip.alertLines.join(", ")}
              </div>
            )}
          </button>
        ))}
      </div>
    </section>
  );
}
