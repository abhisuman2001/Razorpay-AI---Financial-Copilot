import { Routes, Route } from "react-router-dom";
import AppShell from "@/components/AppShell";
import Home from "@/pages/Home";
import Reconciliation from "@/pages/Reconciliation";
import Forecast from "@/pages/Forecast";
import Cfo from "@/pages/Cfo";
import Connect from "@/pages/Connect";

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<Home />} />
        <Route path="reconciliation" element={<Reconciliation />} />
        <Route path="forecast" element={<Forecast />} />
        <Route path="cfo" element={<Cfo />} />
        <Route path="connect" element={<Connect />} />
      </Route>
    </Routes>
  );
}
