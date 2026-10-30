import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { AdminPage } from "./components/AdminPage";
import "./index.css";

// tiny path router — the admin page lives at a non-obvious "backdoor" path;
// change it to your own and keep it private (security by obscurity + login)
const ADMIN_PATH = "/secret-gate/vhid-9f2xq";
const isAdmin = window.location.pathname === ADMIN_PATH;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>{isAdmin ? <AdminPage /> : <App />}</React.StrictMode>
);
