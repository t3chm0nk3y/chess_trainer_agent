import { NavLink, Routes, Route, Navigate } from "react-router-dom";
import AnalysisPage from "./pages/AnalysisPage";
import ConditionsPage from "./pages/ConditionsPage";
import DashboardPage from "./pages/DashboardPage";
import GamesPage from "./pages/GamesPage";
import GameView from "./pages/GameView";
import OpeningsPage from "./pages/OpeningsPage";
import PatternsPage from "./pages/PatternsPage";
import ReportsPage from "./pages/ReportsPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <div className="app">
      <nav className="top-nav">
        <span className="nav-title">Chess Trainer</span>
        <div className="nav-links">
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/games">Games</NavLink>
          <NavLink to="/analysis">Analysis</NavLink>
          <NavLink to="/openings">Openings</NavLink>
          <NavLink to="/patterns">Patterns</NavLink>
          <NavLink to="/conditions">Conditions</NavLink>
          <NavLink to="/reports">Reports</NavLink>
          <NavLink to="/settings">Settings</NavLink>
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
        </Routes>
      </main>
    </div>
  );
}
