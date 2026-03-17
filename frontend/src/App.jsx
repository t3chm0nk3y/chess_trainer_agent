import { useState, useEffect } from "react";
import { NavLink, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import AnalysisPage from "./pages/AnalysisPage";
import ConditionsPage from "./pages/ConditionsPage";
import DashboardPage from "./pages/DashboardPage";
import GamesPage from "./pages/GamesPage";
import HelpPage from "./pages/HelpPage";
import GameView from "./pages/GameView";
import OpeningsPage from "./pages/OpeningsPage";
import PatternsPage from "./pages/PatternsPage";
import ReportsPage from "./pages/ReportsPage";
import SettingsPage from "./pages/SettingsPage";

function StatusDot() {
  const [health, setHealth] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const check = () =>
      fetch("/api/health/detailed")
        .then((r) => r.json())
        .then(setHealth)
        .catch(() => setHealth(null));
    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, []);

  const overall = health?.overall;
  const total = health ? Object.keys(health.components).length : 0;
  const healthyCount = health
    ? Object.values(health.components).filter((c) => c.status === "healthy").length
    : 0;
  const color =
    overall === "healthy" ? "#4caf50" : overall === "degraded" ? "#f44336" : "#9e9e9e";
  const tooltip = health ? `${healthyCount}/${total} healthy` : "Checking...";

  return (
    <span
      onClick={() => navigate("/dashboard")}
      title={tooltip}
      style={{
        display: "inline-block",
        width: 10,
        height: 10,
        borderRadius: "50%",
        backgroundColor: color,
        marginLeft: 8,
        cursor: "pointer",
        verticalAlign: "middle",
        flexShrink: 0,
      }}
    />
  );
}

export default function App() {
  return (
    <div className="app">
      <nav className="top-nav">
        <span className="nav-title">Chess Trainer</span>
        <StatusDot />
        <div className="nav-links">
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/analysis">Analysis</NavLink>
          <NavLink to="/games">Games</NavLink>
          <NavLink to="/openings">Openings</NavLink>
          <NavLink to="/patterns">Patterns</NavLink>
          <NavLink to="/conditions">Conditions</NavLink>
          <NavLink to="/reports">Reports</NavLink>
          <NavLink to="/settings">Settings</NavLink>
          <NavLink to="/help">Help</NavLink>
        </div>
      </nav>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/analysis" element={<AnalysisPage />} />
          <Route path="/games" element={<GamesPage />} />
          <Route path="/games/:id" element={<GameView />} />
          <Route path="/openings" element={<OpeningsPage />} />
          <Route path="/patterns" element={<PatternsPage />} />
          <Route path="/conditions" element={<ConditionsPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/help" element={<HelpPage />} />
        </Routes>
      </main>
    </div>
  );
}
