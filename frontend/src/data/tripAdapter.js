// Convert POST /api/trips/plan responses into the trip shape the UI renders.

const minutes = (seconds) => Math.max(1, Math.round(seconds / 60));

/** Decode a Google encoded polyline into [lat, lng] pairs. */
export function decodePolyline(encoded) {
  if (!encoded) return [];
  const points = [];
  let index = 0;
  let lat = 0;
  let lng = 0;
  while (index < encoded.length) {
    for (const axis of ["lat", "lng"]) {
      let result = 0;
      let shift = 0;
      let byte;
      do {
        byte = encoded.charCodeAt(index++) - 63;
        result |= (byte & 0x1f) << shift;
        shift += 5;
      } while (byte >= 0x20);
      const delta = result & 1 ? ~(result >> 1) : result >> 1;
      if (axis === "lat") lat += delta;
      else lng += delta;
    }
    points.push([lat / 1e5, lng / 1e5]);
  }
  return points;
}

function segmentToStep(segment, index, segments) {
  const duration = minutes(segment.duration_seconds);
  if (segment.mode === "walking") {
    const previous = segments[index - 1];
    const next = segments[index + 1];
    const isTransfer = previous && next && previous.mode !== "walking" && next.mode !== "walking";
    if (isTransfer) {
      return {
        type: "transfer",
        title: `Transfer at ${previous.alighting_stop_name || "station"}`,
        duration,
        waitDuration: 0,
      };
    }
    return {
      type: "walk",
      title: next?.boarding_stop_name || previous?.alighting_stop_name || "Walk",
      duration,
      distance: null,
      polyline: segment.polyline,
    };
  }
  return {
    type: "subway",
    mode: segment.mode,
    line: segment.route_id || segment.mode.toUpperCase(),
    title: `${segment.boarding_stop_name} to ${segment.alighting_stop_name}`,
    duration,
    stops: [segment.boarding_stop_name, segment.alighting_stop_name].filter(Boolean),
    direction: segment.direction || "your direction",
    boardingStationId: segment.boarding_station_id,
    alightingStationId: segment.alighting_station_id,
    polyline: segment.polyline,
  };
}

export function adaptPlannedTrips(response, origin, destination) {
  const routes = response?.routes ?? [];
  const fastest = Math.min(...routes.map((route) => route.duration_seconds));
  const fewestTransfers = Math.min(...routes.map((route) => route.transfer_count));
  const now = Date.now();

  return routes.map((route, index) => {
    const segments = route.segments;
    const steps = segments.map((segment, i) => segmentToStep(segment, i, segments));
    const lines = Array.from(
      new Set(steps.filter((step) => step.type === "subway").map((step) => step.line)),
    );
    const walking = segments
      .filter((segment) => segment.mode === "walking")
      .reduce((total, segment) => total + segment.duration_seconds, 0);
    const departureTime =
      segments.find((segment) => segment.departure_time)?.departure_time ?? new Date(now).toISOString();
    const arrivalTime =
      [...segments].reverse().find((segment) => segment.arrival_time)?.arrival_time ??
      new Date(new Date(departureTime).getTime() + route.duration_seconds * 1000).toISOString();

    let label = `Option ${index + 1}`;
    if (route.duration_seconds === fastest) label = "Fastest";
    else if (route.transfer_count === fewestTransfers) label = "Fewer transfers";

    return {
      id: `planned-${index}`,
      label,
      source: "google",
      duration: minutes(route.duration_seconds),
      departureTime,
      arrivalTime,
      lines,
      walking: Math.round(walking / 60),
      transfers: route.transfer_count,
      origin,
      destination,
      steps,
      path: decodePolyline(route.polyline),
    };
  });
}
