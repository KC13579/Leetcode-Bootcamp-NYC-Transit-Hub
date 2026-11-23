import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

// Web app settings from the Firebase console (Project settings → Your apps).
// These identify the project; they are not secrets.
const config = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

export const firebaseConfigured = Boolean(config.apiKey && config.projectId);

export const auth = firebaseConfigured ? getAuth(initializeApp(config)) : null;
