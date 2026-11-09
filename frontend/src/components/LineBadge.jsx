import { lineColor, lineUsesDarkText } from "../data/mockTrips";

export default function LineBadge({ line }) {
  return (
    <span
      className="line-badge"
      style={{
        backgroundColor: lineColor(line),
        color: lineUsesDarkText(line) ? "#171717" : "#FFFFFF",
      }}
      aria-label={`${line} train`}
    >
      {line}
    </span>
  );
}
