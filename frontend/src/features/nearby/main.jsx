import React from "react";
import ReactDOM from "react-dom/client";

import NearbyApp from "./NearbyApp";
import "./nearby.css";

ReactDOM.createRoot(
  document.getElementById("root")
).render(
  <React.StrictMode>
    <NearbyApp />
  </React.StrictMode>
);
