export default function TransitIcon({ type, size = 18 }) {
  if (type === "walk") {
    return (
      <svg
        className="transit-icon"
        width={size}
        height={size}
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle cx="13" cy="4" r="2" />
        <path d="m10 21 2-6-3-3 2-5 4 3 3 1M7 21l2-6m5 0 4 6M6 10l5-3" />
      </svg>
    );
  }

  if (type === "train") {
    return (
      <svg
        className="transit-icon"
        width={size}
        height={size}
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <rect x="5" y="3" width="14" height="16" rx="3" />
        <path d="M8 7h8M8 12h8M8 22l2-3m6 0 2 3M9 16h.01M15 16h.01" />
      </svg>
    );
  }

  return (
    <svg
      className="transit-icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path d="M5 7h12m0 0-3-3m3 3-3 3M19 17H7m0 0 3-3m-3 3 3 3" />
    </svg>
  );
}
