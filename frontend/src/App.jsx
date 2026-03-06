import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import AnalysisTab from "./pages/AnalysisTab";
import ReportTab from "./pages/ReportTab";
import SettingsTab from "./pages/SettingsTab";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <header className="app-header">
          <h1 className="app-title">Chess Trainer</h1>
          <nav className="app-nav">
            <NavLink to="/" end>
              Analysis
            </NavLink>
            <NavLink to="/report">Report</NavLink>
            <NavLink to="/settings">Settings</NavLink>
          </nav>
        </header>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<AnalysisTab />} />
            <Route path="/report" element={<ReportTab />} />
            <Route path="/settings" element={<SettingsTab />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
