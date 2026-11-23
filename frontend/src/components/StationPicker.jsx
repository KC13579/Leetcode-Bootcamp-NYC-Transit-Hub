import { useEffect, useMemo, useState } from "react";

import { getPlaceSuggestions } from "../api/client";

// Address and place search needs the Google key on the server. After the first
// 503 the picker stops asking and searches stations only.
let placesAvailable = true;

function usePlaceSuggestions(query, enabled) {
  const [places, setPlaces] = useState([]);
  useEffect(() => {
    const term = query.trim();
    if (!enabled || !placesAvailable || term.length < 3) {
      setPlaces([]);
      return undefined;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      getPlaceSuggestions(term, { signal: controller.signal })
        .then((items) => setPlaces(items.slice(0, 4)))
        .catch((error) => {
          if (error.status === 503) placesAvailable = false;
          if (error.name !== "AbortError") setPlaces([]);
        });
    }, 300);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query, enabled]);
  return places;
}

export default function StationPicker({
  label,
  marker,
  placeholder,
  stations,
  savedIds = [],
  value,
  onChange,
}) {
  const [query, setQuery] = useState(value?.name || "");
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    setQuery(value?.name || "");
  }, [value]);

  const matches = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) {
      const saved = savedIds
        .map((id) => stations.find((station) => station.id === id))
        .filter(Boolean);
      const rest = stations.filter((station) => !savedIds.includes(station.id));
      return [...saved, ...rest].slice(0, 6);
    }
    return stations
      .filter(
        (station) =>
          station.name.toLowerCase().includes(term) ||
          station.routes.some((route) => route.toLowerCase() === term),
      )
      .slice(0, 6);
  }, [query, stations, savedIds]);

  const places = usePlaceSuggestions(query, isOpen && !value);

  function handleInput(event) {
    const nextQuery = event.target.value;
    setQuery(nextQuery);
    setIsOpen(true);
    if (value && nextQuery !== value.name) {
      onChange(null);
    }
  }

  function select(item) {
    onChange(item);
    setQuery(item.name);
    setIsOpen(false);
  }

  function selectPlace(place) {
    select({
      id: `place:${place.place_id}`,
      kind: "place",
      place_id: place.place_id,
      name: place.name,
      address: place.address,
      routes: [],
    });
  }

  return (
    <div className="station-picker">
      <span className={`station-marker station-marker--${marker}`} aria-hidden="true" />
      <div className="station-picker__field">
        <label htmlFor={`${marker}-station`}>{label}</label>
        <input
          id={`${marker}-station`}
          type="search"
          autoComplete="off"
          placeholder={placeholder}
          value={query}
          onChange={handleInput}
          onFocus={() => setIsOpen(true)}
          onBlur={() => window.setTimeout(() => setIsOpen(false), 120)}
          aria-expanded={isOpen}
          aria-controls={`${marker}-station-results`}
        />
        {isOpen && (
          <ul
            id={`${marker}-station-results`}
            className="station-picker__results"
            role="listbox"
          >
            {matches.length === 0 && places.length === 0 ? (
              <li className="station-picker__empty">No matching stations</li>
            ) : (
              <>
                {matches.map((station) => (
                  <li key={station.id}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={value?.id === station.id}
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => select(station)}
                    >
                      <span>
                        <strong>
                          {savedIds.includes(station.id) && (
                            <span className="station-picker__saved" aria-label="Saved">★ </span>
                          )}
                          {station.name}
                        </strong>
                        <small>{station.borough ? `${station.borough} · ` : ""}Station</small>
                      </span>
                      <span className="station-picker__routes">
                        {station.routes.slice(0, 5).join(" ")}
                      </span>
                    </button>
                  </li>
                ))}
                {places.map((place) => (
                  <li key={place.place_id}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={value?.place_id === place.place_id}
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => selectPlace(place)}
                    >
                      <span>
                        <strong>{place.name}</strong>
                        <small>{place.address || "Place"}</small>
                      </span>
                      <span className="station-picker__routes">📍</span>
                    </button>
                  </li>
                ))}
              </>
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
