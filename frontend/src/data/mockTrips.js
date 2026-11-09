const LINE_COLORS = {
  "1": "#EE352E",
  "2": "#EE352E",
  "3": "#EE352E",
  "4": "#00933C",
  "5": "#00933C",
  "6": "#00933C",
  "7": "#B933AD",
  A: "#0039A6",
  C: "#0039A6",
  E: "#0039A6",
  B: "#FF6319",
  D: "#FF6319",
  F: "#FF6319",
  M: "#FF6319",
  G: "#6CBE45",
  J: "#996633",
  Z: "#996633",
  L: "#A7A9AC",
  N: "#FCCC0A",
  Q: "#FCCC0A",
  R: "#FCCC0A",
  W: "#FCCC0A",
  S: "#808183",
  SIR: "#0039A6",
};

const DARK_TEXT_LINES = new Set(["N", "Q", "R", "W"]);

export function lineColor(line) {
  return LINE_COLORS[line] || "#5F6368";
}

export function lineUsesDarkText(line) {
  return DARK_TEXT_LINES.has(line);
}

function addMinutes(date, minutes) {
  return new Date(date.getTime() + minutes * 60_000).toISOString();
}

function stationLine(station, index, fallback) {
  return station.routes[index] || station.routes[0] || fallback;
}

function uniqueStops(stops) {
  const seen = new Set();
  return stops.filter((stop) => {
    if (!stop) return false;
    const key = stop.toLowerCase().replace(/[–—-]/g, "-").replace(/\s+/g, " ");
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function itinerarySteps(origin, destination, lines, variant, totalDuration) {
  const walkIn = variant === 1 ? 3 : variant === 2 ? 6 : 4;
  const walkOut = variant === 1 ? 5 : variant === 2 ? 2 : 7;

  if (lines.length === 1) {
    const trainDuration = totalDuration - walkIn - walkOut;
    const stops = uniqueStops([
      origin.name,
      "34 St–Herald Sq",
      "14 St–Union Sq",
      destination.name,
    ]);
    return [
      {
        type: "walk",
        title: origin.name,
        duration: walkIn,
        distance: "0.2 mi",
      },
      {
        type: "subway",
        line: lines[0],
        title: `${origin.name} to ${destination.name}`,
        duration: trainDuration,
        stops,
        direction:
          origin.south_direction_label ||
          destination.north_direction_label ||
          "Downtown",
      },
      {
        type: "walk",
        title: destination.name,
        duration: walkOut,
        distance: "0.3 mi",
      },
    ];
  }

  const transferStation =
    variant === 1 ? "14 St–Union Sq" : variant === 2 ? "34 St–Herald Sq" : "Fulton St";
  const transferDuration = 3;
  const waitDuration = 2;
  const trainTime =
    totalDuration - walkIn - walkOut - transferDuration - waitDuration;
  const firstTrainDuration = Math.ceil(trainTime * 0.55);
  const secondTrainDuration = trainTime - firstTrainDuration;
  const firstMiddle =
    variant === 1 ? "34 St–Herald Sq" : variant === 2 ? "23 St" : "Atlantic Av–Barclays Ctr";
  const secondMiddle =
    variant === 1 ? "Canal St" : variant === 2 ? "W 4 St–Washington Sq" : "Jay St–MetroTech";
  const firstStops = uniqueStops([origin.name, firstMiddle, transferStation]);
  const secondStops = uniqueStops([transferStation, secondMiddle, destination.name]);

  return [
    {
      type: "walk",
      title: origin.name,
      duration: walkIn,
      distance: "0.2 mi",
    },
    {
      type: "subway",
      line: lines[0],
      title: `${origin.name} to ${transferStation}`,
      duration: firstTrainDuration,
      stops: firstStops,
      direction: origin.south_direction_label || "Downtown",
    },
    {
      type: "transfer",
      lines,
      title: `Transfer at ${transferStation}`,
      duration: transferDuration,
      waitDuration,
    },
    {
      type: "subway",
      line: lines[1],
      title: `${transferStation} to ${destination.name}`,
      duration: secondTrainDuration,
      stops: secondStops,
      direction: destination.south_direction_label || "Downtown",
    },
    {
      type: "walk",
      title: destination.name,
      duration: walkOut,
      distance: "0.3 mi",
    },
  ];
}

export function createMockTrips(origin, destination) {
  const now = new Date();
  const primaryLine = stationLine(origin, 0, "A");
  const destinationLine = stationLine(destination, 0, "C");
  const alternateLine = stationLine(origin, 1, "F");
  const secondDestinationLine = stationLine(destination, 1, destinationLine);

  const directLine = origin.routes.find((route) => destination.routes.includes(route));
  const fastestLines = directLine
    ? [directLine]
    : Array.from(new Set([primaryLine, destinationLine]));
  const alternateLines = Array.from(new Set([alternateLine, secondDestinationLine]));
  const simpleLines = directLine ? [directLine] : [primaryLine];

  const templates = [
    {
      id: "fastest",
      label: "Fastest",
      duration: 31,
      departureOffset: 4,
      lines: fastestLines,
      walking: 8,
      transfers: Math.max(0, fastestLines.length - 1),
      variant: 1,
    },
    {
      id: "less-walking",
      label: "Less walking",
      duration: 38,
      departureOffset: 7,
      lines: alternateLines,
      walking: 5,
      transfers: Math.max(0, alternateLines.length - 1),
      variant: 2,
    },
    {
      id: "fewer-transfers",
      label: "Fewer transfers",
      duration: 42,
      departureOffset: 2,
      lines: simpleLines,
      walking: 11,
      transfers: 0,
      variant: 3,
    },
  ];

  return templates.map((trip) => {
    const departureTime = addMinutes(now, trip.departureOffset);
    return {
      ...trip,
      origin,
      destination,
      departureTime,
      arrivalTime: addMinutes(now, trip.departureOffset + trip.duration),
      steps: itinerarySteps(
        origin,
        destination,
        trip.lines,
        trip.variant,
        trip.duration,
      ),
    };
  });
}
