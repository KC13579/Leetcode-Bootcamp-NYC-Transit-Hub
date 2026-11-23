import { useState } from "react";

import { useFavorites } from "../state/favorites";
import { STATUS_TONES } from "../utils/alerts";
import LineBadge from "./LineBadge";

function AccountCard() {
  const { accountsEnabled, authReady, user, signIn, signOut, syncError } = useFavorites();
  const [mode, setMode] = useState("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(await signIn(email.trim(), password, mode === "create"));
    setBusy(false);
  }

  if (!accountsEnabled) {
    return (
      <section className="station-section account-card" aria-labelledby="account-title">
        <h2 id="account-title">Account</h2>
        <p className="station-section__summary">
          Saved items are stored on this device. Accounts that sync across devices turn on
          once the Firebase project is connected.
        </p>
      </section>
    );
  }

  if (!authReady) {
    return <p className="station-section__message station-section__message--muted">Checking sign-in…</p>;
  }

  if (user) {
    return (
      <section className="station-section account-card" aria-labelledby="account-title">
        <div className="station-section__heading">
          <h2 id="account-title">Account</h2>
          <button type="button" className="text-button text-button--small" onClick={signOut}>
            Sign out
          </button>
        </div>
        <p className="station-section__summary">Signed in as {user.email}. Saved items sync to your account.</p>
        {syncError && <p className="station-section__message station-section__message--error">{syncError}</p>}
      </section>
    );
  }

  return (
    <section className="station-section account-card" aria-labelledby="account-title">
      <h2 id="account-title">{mode === "create" ? "Create an account" : "Sign in"}</h2>
      <p className="station-section__summary">
        Sign in to keep your saved stations and lines on every device.
      </p>
      <form className="account-form" onSubmit={submit}>
        <label>
          Email
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Password
          <input
            type="password"
            autoComplete={mode === "create" ? "new-password" : "current-password"}
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button className="button button--primary button--full" type="submit" disabled={busy}>
          {mode === "create" ? "Create account" : "Sign in"}
        </button>
      </form>
      <button
        type="button"
        className="text-button text-button--small"
        onClick={() => {
          setMode(mode === "create" ? "signin" : "create");
          setError(null);
        }}
      >
        {mode === "create" ? "Already have an account? Sign in" : "New here? Create an account"}
      </button>
    </section>
  );
}

export default function SavedPanel({ stations, statuses, onOpenStation, onOpenLine, onGoPlan }) {
  const { favorites, toggleFavorite } = useFavorites();
  const stationsById = new Map(stations.map((station) => [station.id, station]));
  const statusByRoute = new Map((statuses ?? []).map((item) => [item.route, item]));
  const savedStations = favorites
    .filter((item) => item.kind === "station")
    .map((item) => stationsById.get(item.target_id))
    .filter(Boolean);
  const savedRoutes = favorites.filter((item) => item.kind === "route").map((item) => item.target_id);

  return (
    <section className="saved-page" aria-labelledby="saved-title">
      <div className="detail-hero">
        <span className="route-card__label">Your transit</span>
        <h1 id="saved-title">Saved</h1>
        <p>Your usual stations and lines, one tap away.</p>
      </div>

      <section className="station-section" aria-labelledby="saved-stations-title">
        <h2 id="saved-stations-title">Stations</h2>
        {savedStations.length === 0 ? (
          <p className="station-section__summary">
            Open a station and tap <strong>Save</strong> to add it here.{" "}
            <button type="button" className="text-button text-button--small" onClick={onGoPlan}>
              Find a station
            </button>
          </p>
        ) : (
          <ul className="saved-list">
            {savedStations.map((station) => (
              <li key={station.id}>
                <button type="button" className="saved-item" onClick={() => onOpenStation(station)}>
                  <strong>{station.name}</strong>
                  <span className="saved-item__lines">
                    {station.routes.map((route) => (
                      <LineBadge line={route} key={route} />
                    ))}
                  </span>
                </button>
                <button
                  type="button"
                  className="saved-remove"
                  onClick={() => toggleFavorite("station", station.id)}
                  aria-label={`Remove ${station.name}`}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="station-section" aria-labelledby="saved-lines-title">
        <h2 id="saved-lines-title">Lines</h2>
        {savedRoutes.length === 0 ? (
          <p className="station-section__summary">
            Open a line from the Status tab and tap <strong>Save</strong> to follow it.
          </p>
        ) : (
          <ul className="saved-list">
            {savedRoutes.map((route) => {
              const status = statusByRoute.get(route)?.status;
              return (
                <li key={route}>
                  <button type="button" className="saved-item" onClick={() => onOpenLine(route)}>
                    <LineBadge line={route} />
                    {status && (
                      <span className={`status-chip status-chip--${STATUS_TONES[status] || "muted"}`}>{status}</span>
                    )}
                  </button>
                  <button
                    type="button"
                    className="saved-remove"
                    onClick={() => toggleFavorite("route", route)}
                    aria-label={`Remove ${route} line`}
                  >
                    ×
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <AccountCard />
    </section>
  );
}
