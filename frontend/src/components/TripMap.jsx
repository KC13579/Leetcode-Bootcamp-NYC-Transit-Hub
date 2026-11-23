import { useEffect, useRef } from "react";
import L from "leaflet";

import { lineColor } from "../data/mockTrips";
import { decodePolyline } from "../data/tripAdapter";

function point(place) {
  return place && Number.isFinite(place.latitude) && Number.isFinite(place.longitude)
    ? [place.latitude, place.longitude]
    : null;
}

/**
 * Small map of the selected trip. Real plans draw each segment's Google polyline
 * in its line color; demo plans only know the two stations, so they draw a dashed
 * straight line between them.
 */
export default function TripMap({ trip }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return undefined;
    const map = L.map(containerRef.current, {
      zoomControl: false,
      attributionControl: false,
      scrollWheelZoom: false,
    });
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19 }).addTo(map);

    const bounds = [];
    trip.steps.forEach((step) => {
      const path = decodePolyline(step.polyline);
      if (!path.length) return;
      bounds.push(...path);
      L.polyline(path, {
        color: step.type === "subway" ? lineColor(step.line) : "#c1c6cc",
        weight: step.type === "subway" ? 6 : 4,
        dashArray: step.type === "subway" ? null : "4 8",
        opacity: 0.95,
      }).addTo(map);
    });

    if (!bounds.length && trip.path?.length) {
      bounds.push(...trip.path);
      L.polyline(trip.path, { color: "#168dcc", weight: 5 }).addTo(map);
    }

    const start = point(trip.origin);
    const end = point(trip.destination);
    if (!bounds.length && start && end) {
      bounds.push(start, end);
      L.polyline([start, end], {
        color: lineColor(trip.lines[0]),
        weight: 4,
        dashArray: "8 10",
      }).addTo(map);
    }

    [
      [start ?? bounds[0], "#168dcc"],
      [end ?? bounds[bounds.length - 1], "#f5f6f7"],
    ].forEach(([position, color]) => {
      if (!position) return;
      L.circleMarker(position, {
        radius: 7,
        color: "#0b0e12",
        weight: 2,
        fillColor: color,
        fillOpacity: 1,
      }).addTo(map);
    });

    if (bounds.length) map.fitBounds(bounds, { padding: [28, 28], maxZoom: 15 });
    else map.setView([40.73, -73.95], 11);

    return () => map.remove();
  }, [trip]);

  return <div ref={containerRef} className="trip-map" aria-label="Map of the selected route" />;
}
