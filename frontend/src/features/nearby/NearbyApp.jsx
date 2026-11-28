import { useState } from "react";

export default function NearbyApp() {
  const [location, setLocation] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function findLocation() {
    setError("");
    setLocation(null);

    if (!navigator.geolocation) {
      setError("Geolocation is not supported.");
      return;
    }

    setLoading(true);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        });

        setLoading(false);
      },

      () => {
        setError("Unable to access your location.");
        setLoading(false);
      },

      { timeout: 10000 }
    );
  }

  return (
    <main className="nearby-app">

      <header className="nearby-header">
        <h1>NYC Transit Hub</h1>
        <a href="/">Back to Trip Planner</a>
      </header>

      <section className="nearby-panel">

        <h2>Smart Nearby Station Finder</h2>

        <p>
          Find nearby subway stations and the best
          train to catch based on your location.
        </p>

        <button
          className="nearby-button"
          onClick={findLocation}
          disabled={loading}
        >
          {loading ? "Finding location..." : "Use My Location"}
        </button>

        {error && (
          <p className="nearby-error">{error}</p>
        )}

        {location && (
          <div className="nearby-location">
            <h3>Location detected successfully</h3>
            <p>Latitude: {location.latitude.toFixed(6)}</p>
            <p>Longitude: {location.longitude.toFixed(6)}</p>
          </div>
        )}

      </section>

    </main>
  );
}
