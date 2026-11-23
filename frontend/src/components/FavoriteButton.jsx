import { useFavorites } from "../state/favorites";

export default function FavoriteButton({ kind, targetId, label }) {
  const { isFavorite, toggleFavorite } = useFavorites();
  const saved = isFavorite(kind, targetId);

  return (
    <button
      type="button"
      className={`favorite-button${saved ? " favorite-button--saved" : ""}`}
      onClick={() => toggleFavorite(kind, targetId)}
      aria-pressed={saved}
      aria-label={saved ? `Remove ${label} from saved` : `Save ${label}`}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m12 3.5 2.6 5.3 5.9.9-4.25 4.1 1 5.8L12 16.9l-5.25 2.7 1-5.8L3.5 9.7l5.9-.9L12 3.5Z" />
      </svg>
      {saved ? "Saved" : "Save"}
    </button>
  );
}
