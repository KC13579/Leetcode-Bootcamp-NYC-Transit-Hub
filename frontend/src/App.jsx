import { useCallback, useEffect, useMemo, useState } from "react";

import { getAlerts, getServiceStatus, getStations, planTrip } from "./api/client";
import BottomNav from "./components/BottomNav";
import LineDetails from "./components/LineDetails";
import RouteOptions from "./components/RouteOptions";
import SavedPanel from "./components/SavedPanel";
import ServiceStatus from "./components/ServiceStatus";
import StationDetails from "./components/StationDetails";
import StationPicker from "./components/StationPicker";
import TransitMap from "./components/TransitMap";
import TripDetails from "./components/TripDetails";
import { createMockTrips } from "./data/mockTrips";
import { adaptPlannedTrips } from "./data/tripAdapter";
import { useFavorites } from "./state/favorites";

const STATUS_REFRESH_MS = 60_000;
const TAB_ROOTS = { plan: "search", status: "status", saved: "saved" };

function useServiceStatus() {
  const [state, setState] = useState({ status: "loading", data: null, loadedAt: null });
  const [reloadKey, setReloadKey] = useState(0);
  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setState((previous) => ({ ...previous, status: previous.data ? "refreshing" : "loading" }));
    getServiceStatus({ signal: controller.signal })
      .then((data) => setState({ status: "ready", data, loadedAt: new Date() }))
      .catch((error) => {
        if (error.name !== "AbortError") setState((previous) => ({ ...previous, status: "error" }));
      });
    return () => controller.abort();
  }, [reloadKey]);

  useEffect(() => {
    const timer = setInterval(reload, STATUS_REFRESH_MS);
    return () => clearInterval(timer);
  }, [reload]);

  return { state, reload };
}

const locationOf = (item) =>
  item.kind === "place" ? { place_id: item.place_id } : { station_id: item.id };

export default function App() {
  const { favorites } = useFavorites();
  const [stations, setStations] = useState([]);
  const [stationsLoading, setStationsLoading] = useState(true);
  const [stationsError, setStationsError] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [origin, setOrigin] = useState(null);
  const [destination, setDestination] = useState(null);
  const [plan, setPlan] = useState({ status: "idle", trips: [], notice: null });
  const { state: serviceStatus, reload: reloadStatus } = useServiceStatus();

  // Each tab keeps its own page stack so switching tabs never loses your place.
  const [tab, setTab] = useState("plan");
  const [stacks, setStacks] = useState({
    plan: [{ view: "search" }],
    status: [{ view: "status" }],
    saved: [{ view: "saved" }],
  });
  const page = stacks[tab][stacks[tab].length - 1];

  const scrollTop = () => window.scrollTo({ top: 0, behavior: "smooth" });

  const push = useCallback((next) => {
    setStacks((current) => ({ ...current, [tab]: [...current[tab], next] }));
    scrollTop();
  }, [tab]);

  const back = useCallback(() => {
    setStacks((current) => ({
      ...current,
      [tab]: current[tab].length > 1 ? current[tab].slice(0, -1) : current[tab],
    }));
  }, [tab]);

  function switchTab(nextTab) {
    if (nextTab === tab) {
      // Tapping the active tab returns to its first page.
      setStacks((current) => ({ ...current, [tab]: [{ view: TAB_ROOTS[tab] }] }));
    }
    setTab(nextTab);
    scrollTop();
  }

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

  const trips = useMemo(
    () =>
      plan.trips.map((trip) => {
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
      }),
    [plan.trips, alerts],
  );

  const savedStationIds = favorites.filter((item) => item.kind === "station").map((item) => item.target_id);
  const savedRoutes = favorites.filter((item) => item.kind === "route").map((item) => item.target_id);
  const problemLines = (serviceStatus.data ?? []).filter((item) =>
    ["Delays", "Rerouted", "Suspended"].includes(item.status),
  ).length;

  const sameStation = origin && destination && origin.id === destination.id;
  const canPlan = origin && destination && !sameStation;

  async function submitPlan(event) {
    event.preventDefault();
    if (!canPlan) return;
    push({ view: "options" });
    setPlan({ status: "loading", trips: [], notice: null });
    try {
      const response = await planTrip(locationOf(origin), locationOf(destination));
      const planned = adaptPlannedTrips(response, origin, destination);
      setPlan({
        status: "ready",
        trips: planned,
        notice: planned.length ? null : "No transit routes were found between these places.",
      });
    } catch (error) {
      const bothStations = origin.kind !== "place" && destination.kind !== "place";
      if (error.status === 503 && bothStations) {
        setPlan({
          status: "ready",
          trips: createMockTrips(origin, destination),
          notice: "Demo routes: live trip planning turns on when the server has a Google Maps key.",
        });
      } else {
        setPlan({
          status: "error",
          trips: [],
          notice: error.detail || "Routes could not be planned right now. Please try again.",
        });
      }
    }
  }

  function swapStations() {
    setOrigin(destination);
    setDestination(origin);
  }

  const openStation = (station) => push({ view: "station", station });
  const openLine = (route) => push({ view: "line", route });
  const editTrip = () => setStacks((current) => ({ ...current, plan: [{ view: "search" }] }));

  const isMapPage = page.view === "search";

  return (
    <div className="app-shell">
      <main className={isMapPage ? "main--map" : ""}>
        {page.view === "search" && (
          <section className="map-screen" aria-label="Route planner">
            <TransitMap stations={stations} onStationSelect={openStation} />
            <div className="planner planner--map">
              <form className="planner-card" onSubmit={submitPlan}>
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
                      placeholder="Station, address or place"
                      stations={stations}
                      savedIds={savedStationIds}
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
                      placeholder="Station, address or place"
                      stations={stations}
                      savedIds={savedStationIds}
                      value={destination}
                      onChange={setDestination}
                    />
                  </div>

                  {(origin || destination) && (
                    <div className="station-links">
                      {[origin, destination]
                        .filter((item) => item && item.kind !== "place")
                        .filter((station, index, list) => list.findIndex((s) => s.id === station.id) === index)
                        .map((station) => (
                          <button
                            type="button"
                            className="text-button text-button--small"
                            key={station.id}
                            onClick={() => openStation(station)}
                          >
                            {station.name} station info
                          </button>
                        ))}
                    </div>
                  )}

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
            </div>
          </section>
        )}

        {page.view === "options" && origin && destination && (
          <RouteOptions
            origin={origin}
            destination={destination}
            trips={trips}
            status={plan.status}
            notice={plan.notice}
            onSelect={(trip) => push({ view: "details", trip })}
            onModify={editTrip}
          />
        )}

        {page.view === "details" && (
          <TripDetails trip={page.trip} onBack={back} onEdit={editTrip} />
        )}

        {page.view === "station" && (
          <StationDetails
            key={page.station.id}
            station={page.station}
            onBack={back}
            onOpenLine={openLine}
          />
        )}

        {page.view === "status" && (
          <ServiceStatus
            state={serviceStatus}
            onSelectLine={openLine}
            onReload={reloadStatus}
            savedRoutes={savedRoutes}
          />
        )}

        {page.view === "line" && (
          <LineDetails
            key={page.route}
            route={page.route}
            statusItem={serviceStatus.data?.find((item) => item.route === page.route)}
            stations={stations}
            onBack={back}
            onOpenStation={openStation}
          />
        )}

        {page.view === "saved" && (
          <SavedPanel
            stations={stations}
            statuses={serviceStatus.data}
            onOpenStation={openStation}
            onOpenLine={openLine}
            onGoPlan={() => switchTab("plan")}
          />
        )}
      </main>
      <BottomNav active={tab} onChange={switchTab} alertCount={problemLines} />
    </div>
  );
}
