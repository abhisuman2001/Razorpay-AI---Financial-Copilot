import { Routes, Route, Navigate } from "react-router-dom";
import AppShell from "@/components/AppShell";
import AuthGuard from "@/components/AuthGuard";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Home from "@/pages/Home";
import Reconciliation from "@/pages/Reconciliation";
import Forecast from "@/pages/Forecast";
import Cfo from "@/pages/Cfo";
import Connect from "@/pages/Connect";
import Profile from "@/pages/Profile";

// BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <Routes>
      {/* ── Public routes ────────────────────────────────────────────────── */}
      <Route path="/landing" element={<Landing />} />
      <Route path="/login" element={<Login />} />

      {/* ── Protected routes (require active session) ────────────────────── */}
      <Route element={<AuthGuard />}>
        <Route element={<AppShell />}>
          <Route index element={<Home />} />
          <Route path="reconciliation" element={<Reconciliation />} />
          <Route path="forecast" element={<Forecast />} />
          <Route path="cfo" element={<Cfo />} />
          <Route path="connect" element={<Connect />} />
          <Route path="profile" element={<Profile />} />
        </Route>
      </Route>

      {/* ── Fallback ─────────────────────────────────────────────────────── */}
      <Route path="*" element={<Navigate to="/landing" replace />} />
    </Routes>
  );
}
