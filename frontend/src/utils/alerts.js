// Helpers that turn raw MTA alert fields into rider-friendly wording.

const CAUSES = {
  TECHNICAL_PROBLEM: "Technical problem",
  STRIKE: "Strike",
  DEMONSTRATION: "Demonstration",
  ACCIDENT: "Accident",
  HOLIDAY: "Holiday schedule",
  WEATHER: "Weather",
  MAINTENANCE: "Maintenance",
  CONSTRUCTION: "Construction / planned work",
  POLICE_ACTIVITY: "Police activity",
  MEDICAL_EMERGENCY: "Medical emergency",
};

export const DISRUPTIONS = {
  suspension: { label: "Suspended", tone: "bad", meaning: "Trains are not running on part or all of this line." },
  reroute: { label: "Rerouted", tone: "warn", meaning: "Trains run on a different path and may skip or add stops." },
  delay: { label: "Delays", tone: "warn", meaning: "Expect longer waits and slower trips." },
  skip: { label: "Skipped stops", tone: "warn", meaning: "Some stations are bypassed. Check your stop before boarding." },
  service_change: { label: "Service change", tone: "muted", meaning: "The usual service pattern is changed." },
  other: { label: "Notice", tone: "muted", meaning: "Information about this line." },
};

/** Classify an alert, falling back to its wording when MTA's effect code is generic. */
export function disruptionKind(alert) {
  if (alert.disruption_type && alert.disruption_type !== "other") {
    return alert.disruption_type;
  }
  const text = `${alert.title} ${alert.description || ""}`.toLowerCase();
  if (/suspend|not running|no [a-z0-9 ]*trains? (between|in|at)/.test(text)) return "suspension";
  if (/rerout|detour|run via|running via/.test(text)) return "reroute";
  if (/delay|slower|longer wait/.test(text)) return "delay";
  if (/skip|bypass|not stop/.test(text)) return "skip";
  if (/express|local|stopping at|no trains|board/.test(text)) return "service_change";
  return "other";
}

export function causeLabel(cause) {
  return CAUSES[cause] || null;
}

/** MTA titles put lines in brackets, e.g. "[E] trains are delayed"; drop the brackets. */
export function cleanAlertText(text) {
  return (text || "")
    .replace(/\]\s*\[/g, "] and [")
    .replace(/\[([A-Z0-9]{1,3})\]/g, "$1")
    .replace(/(\w) and (\w) and /g, "$1, $2 and ")
    .trim();
}

export function dateTimeLabel(value) {
  if (!value) return null;
  return new Date(value).toLocaleString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function timeLabel(value) {
  if (!value) return null;
  return new Date(value).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

export const STATUS_TONES = {
  "Good Service": "good",
  Delays: "warn",
  Rerouted: "warn",
  Suspended: "bad",
  "Service Change": "muted",
  Unknown: "muted",
};

// Lines grouped the way they appear on MTA maps and station signs.
export const LINE_GROUPS = [
  ["1", "2", "3"],
  ["4", "5", "6"],
  ["7"],
  ["A", "C", "E"],
  ["B", "D", "F", "M"],
  ["G"],
  ["J", "Z"],
  ["L"],
  ["N", "Q", "R", "W"],
  ["S"],
  ["SIR"],
];
