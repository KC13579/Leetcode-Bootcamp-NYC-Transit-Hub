import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
} from "firebase/auth";

import { deleteFavorite, listFavorites, saveFavorite } from "../api/client";
import { auth, firebaseConfigured } from "../auth/firebase";

const DEVICE_KEY = "nyc-transit-hub:favorites";
const FavoritesContext = createContext(null);

const sameItem = (a, b) => a.kind === b.kind && a.target_id === b.target_id;

function readDeviceFavorites() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(DEVICE_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeDeviceFavorites(items) {
  try {
    window.localStorage.setItem(DEVICE_KEY, JSON.stringify(items));
  } catch {
    // Private browsing can block storage; favorites still work for this visit.
  }
}

function authMessage(error) {
  const code = error?.code || "";
  if (code.includes("invalid-credential") || code.includes("wrong-password")) {
    return "Email or password is incorrect.";
  }
  if (code.includes("user-not-found")) return "No account uses this email.";
  if (code.includes("email-already-in-use")) return "An account already uses this email.";
  if (code.includes("weak-password")) return "Use a password with at least 6 characters.";
  if (code.includes("invalid-email")) return "Enter a valid email address.";
  return "Sign-in failed. Please try again.";
}

/**
 * Saved stations and lines. Signed-in users are stored in Firestore through the
 * backend's /api/me/favorites endpoints; otherwise items are kept on this device.
 */
export function FavoritesProvider({ children }) {
  const [user, setUser] = useState(null);
  const [authReady, setAuthReady] = useState(!firebaseConfigured);
  const [favorites, setFavorites] = useState(readDeviceFavorites);
  const [syncError, setSyncError] = useState(null);

  useEffect(() => {
    if (!auth) return undefined;
    return onAuthStateChanged(auth, (nextUser) => {
      setUser(nextUser);
      setAuthReady(true);
    });
  }, []);

  // Load the account's favorites after sign-in, carrying over device-only items.
  useEffect(() => {
    if (!user) {
      setFavorites(readDeviceFavorites());
      return undefined;
    }
    let active = true;
    (async () => {
      try {
        const token = await user.getIdToken();
        const remote = await listFavorites(token);
        const local = readDeviceFavorites().filter(
          (item) => !remote.some((saved) => sameItem(saved, item)),
        );
        await Promise.all(local.map((item) => saveFavorite(token, item.kind, item.target_id)));
        writeDeviceFavorites([]);
        if (active) {
          setFavorites([...remote, ...local]);
          setSyncError(null);
        }
      } catch (error) {
        if (active) {
          setSyncError(
            error.status === 503
              ? "The server is not connected to Firebase yet, so saved items stay on this device."
              : "Saved items could not be loaded from your account.",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [user]);

  const isFavorite = useCallback(
    (kind, targetId) => favorites.some((item) => sameItem(item, { kind, target_id: targetId })),
    [favorites],
  );

  const toggleFavorite = useCallback(
    async (kind, targetId) => {
      const item = { kind, target_id: targetId };
      const saved = favorites.some((existing) => sameItem(existing, item));
      const next = saved
        ? favorites.filter((existing) => !sameItem(existing, item))
        : [...favorites, item];
      setFavorites(next);

      if (!user || syncError) {
        writeDeviceFavorites(next);
        return;
      }
      try {
        const token = await user.getIdToken();
        if (saved) await deleteFavorite(token, kind, targetId);
        else await saveFavorite(token, kind, targetId);
      } catch {
        setFavorites(favorites);
        setSyncError("That change could not be saved. Please try again.");
      }
    },
    [favorites, user, syncError],
  );

  const signIn = useCallback(async (email, password, createAccount) => {
    try {
      if (createAccount) await createUserWithEmailAndPassword(auth, email, password);
      else await signInWithEmailAndPassword(auth, email, password);
      return null;
    } catch (error) {
      return authMessage(error);
    }
  }, []);

  const signOut = useCallback(async () => {
    await firebaseSignOut(auth);
    setSyncError(null);
  }, []);

  const value = useMemo(
    () => ({
      accountsEnabled: firebaseConfigured,
      authReady,
      user,
      favorites,
      syncError,
      isFavorite,
      toggleFavorite,
      signIn,
      signOut,
    }),
    [authReady, user, favorites, syncError, isFavorite, toggleFavorite, signIn, signOut],
  );

  return <FavoritesContext.Provider value={value}>{children}</FavoritesContext.Provider>;
}

export function useFavorites() {
  return useContext(FavoritesContext);
}
