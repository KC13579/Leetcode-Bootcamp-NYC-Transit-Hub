import { useEffect, useMemo, useState } from "react";

import { getAlerts, getStations } from "./api/client";
import RouteOptions from "./components/RouteOptions";
import StationPicker from "./components/StationPicker";
import TripDetails from "./components/TripDetails";
import { createMockTrips } from "./data/mockTrips";

export default function App() {
  const [stations, setStations] = useState([]);
  const [stationsLoading, setStationsLoading] = useState(true);
  const [stationsError, setStationsError] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [origin, setOrigin] = useState(null);
  const [destination, setDestination] = useState(null);
  const [view, setView] = useState("search");
  const [selectedTrip, setSelectedTrip] = useState(null);

  useEffect(() => {
    let active = true;
    getStations()
      .then((data) => {
        if (active) {
          setStations(data);
          setStationsError(false);
        }
      })
      .catch(() => {
        if (active) setStationsError(true);
      })
      .finally(() => {
        if (active) setStationsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    getAlerts()
      .then((data) => {
        if (active) setAlerts(data);
      })
      .catch(() => {
        if (active) setAlerts([]);
      });
    return () => {
      active = false;
    };
  }, []);

  const trips = useMemo(() => {
    if (!origin || !destination) return [];
    return createMockTrips(origin, destination).map((trip) => {
      const matchingAlerts = alerts.filter((alert) =>
        alert.routes.some((route) => trip.lines.includes(route)),
      );
      return {
        ...trip,
        alerts: matchingAlerts,
        alertLines: Array.from(
          new Set(
            matchingAlerts.flatMap((alert) =>
              alert.routes.filter((route) => trip.lines.includes(route)),
            ),
          ),
        ),
      };
    });
  }, [origin, destination, alerts]);

  const sameStation = origin && destination && origin.id === destination.id;
  const canPlan = origin && destination && !sameStation;

  function planTrip(event) {
    event.preventDefault();
    if (!canPlan) return;
    setSelectedTrip(null);
    setView("options");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function swapStations() {
    setOrigin(destination);
    setDestination(origin);
  }

  function selectTrip(trip) {
    setSelectedTrip(trip);
    setView("details");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function editTrip() {
    setSelectedTrip(null);
    setView("search");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div className="app-shell">
      <main>
        {view === "search" && (
          <section className="planner" aria-label="Route planner">
            <form className="planner-card" onSubmit={planTrip}>
              {stationsLoading && (
                <div className="state-message">
                  <span className="state-message__spinner" aria-hidden="true" />
                  Loading stations…
                </div>
              )}

              {stationsError && (
                <div className="state-message state-message--error">
                  <strong>Stations could not be loaded.</strong>
                  <span>Make sure the FastAPI backend is running on port 8000.</span>
                  <button type="button" onClick={() => window.location.reload()}>
                    Try again
                  </button>
                </div>
              )}

              {!stationsLoading && !stationsError && (
                <>
                  <div className="planner-card__fields">
                    <StationPicker
                      label="Start"
                      marker="origin"
                      placeholder="Enter starting station"
                      stations={stations}
                      value={origin}
                      onChange={setOrigin}
                    />

                    <button
                      className="swap-button"
                      type="button"
                      onClick={swapStations}
                      aria-label="Swap start and destination"
                      disabled={!origin && !destination}
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M7 4v14m0 0-3-3m3 3 3-3M17 20V6m0 0-3 3m3-3 3 3" />
                      </svg>
                    </button>

                    <StationPicker
                      label="Destination"
                      marker="destination"
                      placeholder="Enter destination station"
                      stations={stations}
                      value={destination}
                      onChange={setDestination}
                    />
                  </div>

                  {sameStation && (
                    <p className="form-error">Start and destination must be different.</p>
                  )}

                  <button className="button button--primary button--full" type="submit" disabled={!canPlan}>
                    View route options
                    <span aria-hidden="true">→</span>
                  </button>
                </>
              )}
            </form>
          </section>
        )}

        {view === "options" && origin && destination && (
          <RouteOptions
            origin={origin}
            destination={destination}
            trips={trips}
            onSelect={selectTrip}
            onModify={editTrip}
          />
        )}

        {view === "details" && selectedTrip && (
          <TripDetails
            trip={selectedTrip}
            onBack={() => setView("options")}
            onEdit={editTrip}
          />
        )}
      </main>
    </div>
  );
}
