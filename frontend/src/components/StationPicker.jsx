import { useEffect, useMemo, useState } from "react";

export default function StationPicker({
  label,
  marker,
  placeholder,
  stations,
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
    if (!term) return stations.slice(0, 6);
    return stations
      .filter(
        (station) =>
          station.name.toLowerCase().includes(term) ||
          station.routes.some((route) => route.toLowerCase() === term),
      )
      .slice(0, 6);
  }, [query, stations]);

  function handleInput(event) {
    const nextQuery = event.target.value;
    setQuery(nextQuery);
    setIsOpen(true);
    if (value && nextQuery !== value.name) {
      onChange(null);
    }
  }

  function selectStation(station) {
    onChange(station);
    setQuery(station.name);
    setIsOpen(false);
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
            {matches.length === 0 ? (
              <li className="station-picker__empty">No matching stations</li>
            ) : (
              matches.map((station) => (
                <li key={station.id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={value?.id === station.id}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => selectStation(station)}
                  >
                    <span>
                      <strong>{station.name}</strong>
                      <small>{station.borough} · {station.id}</small>
                    </span>
                    <span className="station-picker__routes">
                      {station.routes.slice(0, 5).join(" ")}
                    </span>
                  </button>
                </li>
              ))
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
