const TABS = [
  {
    id: "plan",
    label: "Plan",
    icon: "M4 19 9 5l6 14 5-9M4 19h16",
  },
  {
    id: "status",
    label: "Status",
    icon: "M12 4v9m0 4v.5M10.3 4.9 2.8 18a2 2 0 0 0 1.7 3h15a2 2 0 0 0 1.7-3L13.7 4.9a2 2 0 0 0-3.4 0Z",
  },
  {
    id: "saved",
    label: "Saved",
    icon: "m12 3.5 2.6 5.3 5.9.9-4.25 4.1 1 5.8L12 16.9l-5.25 2.7 1-5.8L3.5 9.7l5.9-.9L12 3.5Z",
  },
];

export default function BottomNav({ active, onChange, alertCount }) {
  return (
    <nav className="bottom-nav" aria-label="Main">
      {TABS.map((tab) => (
        <button
          type="button"
          key={tab.id}
          className={`bottom-nav__tab${active === tab.id ? " bottom-nav__tab--active" : ""}`}
          aria-current={active === tab.id ? "page" : undefined}
          onClick={() => onChange(tab.id)}
        >
          <span className="bottom-nav__icon">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d={tab.icon} />
            </svg>
            {tab.id === "status" && alertCount > 0 && (
              <span className="bottom-nav__badge" aria-label={`${alertCount} lines with problems`}>
                {alertCount}
              </span>
            )}
          </span>
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
