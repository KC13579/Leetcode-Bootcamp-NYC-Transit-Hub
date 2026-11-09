import { useEffect, useRef, useState } from "react";
import L from "leaflet";

import { getMapNetwork } from "../api/client";

const NYC_CENTER = [40.715, -73.96];
const NYC_BOUNDS = [
  [40.47, -74.32],
  [40.94, -73.64],
];

function stationPopup(station) {
  const content = document.createElement("div");
  const name = document.createElement("strong");
  name.textContent = station.name;
  content.append(name);

  if (station.routes.length) {
    const routes = document.createElement("span");
    routes.textContent = station.routes.join(" · ");
    content.append(routes);
  }
  return content;
}

export default function TransitMap({ stations }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const lineLayerRef = useRef(null);
  const stationLayerRef = useRef(null);
  const [network, setNetwork] = useState(null);
  const [networkError, setNetworkError] = useState(false);

  useEffect(() => {
    let active = true;
    getMapNetwork()
      .then((data) => {
        if (active) setNetwork(data);
      })
      .catch(() => {
        if (active) setNetworkError(true);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: NYC_CENTER,
      zoom: 11,
      minZoom: 10,
      maxZoom: 17,
      maxBounds: NYC_BOUNDS,
      zoomControl: false,
      attributionControl: false,
    });

    L.control.attribution({ position: "topleft", prefix: false }).addTo(map);
    L.tileLayer(
      "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        maxZoom: 19,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      },
    ).addTo(map);
    L.control.zoom({ position: "topright" }).addTo(map);

    map.createPane("route-casing").style.zIndex = "410";
    map.createPane("routes").style.zIndex = "420";
    map.createPane("stations").style.zIndex = "430";

    lineLayerRef.current = L.layerGroup().addTo(map);
    stationLayerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current || !network) return;
    const layer = lineLayerRef.current;
    layer.clearLayers();

    network.lines.forEach((line) => {
      L.polyline(line.coordinates, {
        pane: "route-casing",
        color: "#080a0d",
        weight: 8,
        opacity: 0.86,
        interactive: false,
      }).addTo(layer);
      L.polyline(line.coordinates, {
        pane: "routes",
        color: line.color,
        weight: 5,
        opacity: 0.96,
        lineCap: "round",
        lineJoin: "round",
        interactive: false,
      }).addTo(layer);
    });
  }, [network]);

  useEffect(() => {
    const map = mapRef.current;
    const layer = stationLayerRef.current;
    if (!map || !layer) return;

    layer.clearLayers();
    const markers = stations.map((station) => {
      const marker = L.circleMarker([station.latitude, station.longitude], {
        pane: "stations",
        radius: station.routes.length > 1 ? 4.5 : 3.2,
        color: "#0b0e12",
        weight: 1.5,
        fillColor: "#f4f5f6",
        fillOpacity: 1,
      }).addTo(layer);

      marker.bindPopup(stationPopup(station), {
        className: "station-popup",
        closeButton: false,
        offset: [0, -2],
      });
      return { marker, station };
    });

    function updateLabels() {
      const zoom = map.getZoom();
      markers.forEach(({ marker, station }) => {
        marker.setRadius(zoom >= 14 ? 5 : station.routes.length > 1 ? 4.5 : 3.2);
        marker.unbindTooltip();
        marker.bindTooltip(station.name, {
          className: "station-tooltip",
          direction: "top",
          offset: [0, -5],
          permanent: zoom >= 14 || (zoom >= 13 && station.routes.length > 1),
          opacity: 1,
        });
      });
    }

    updateLabels();
    map.on("zoomend", updateLabels);
    return () => {
      map.off("zoomend", updateLabels);
    };
  }, [stations]);

  return (
    <div className="transit-map" aria-label="Interactive New York City subway map">
      <div ref={containerRef} className="transit-map__canvas" />
      {!network && !networkError && (
        <div className="transit-map__status">Loading subway lines…</div>
      )}
      {networkError && (
        <div className="transit-map__status transit-map__status--error">
          Subway lines unavailable
        </div>
      )}
    </div>
  );
}
