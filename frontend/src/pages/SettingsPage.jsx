import { useEffect, useState } from "react";
import { importGames } from "../api/client";

export default function SettingsPage() {
  const [config, setConfig] = useState(null);
  const [importCount, setImportCount] = useState("100");
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [gameCount, setGameCount] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);
  const [restarting, setRestarting] = useState(false);

  // Editable fields
  const [username, setUsername] = useState("");
  const [token, setToken] = useState("");
  const [depth, setDepth] = useState("18");

  useEffect(() => {
    fetch("/api/config")
      .then((r) => r.json())
      .then((c) => {
        setConfig(c);
        setUsername(c.username || "");
        setDepth(String(c.stockfish_depth || 18));
      })
      .catch(() => {});
    fetch("/api/dashboard")
      .then((r) => r.json())
      .then((d) => setGameCount(d.total_games))
      .catch(() => {});
  }, []);

  const handleImport = async () => {
    setImporting(true);
    setImportResult(null);
    try {
      const maxGames = importCount === "all" ? null : parseInt(importCount);
      const result = await importGames(maxGames);
      setImportResult(result);
      fetch("/api/dashboard")
        .then((r) => r.json())
        .then((d) => setGameCount(d.total_games))
        .catch(() => {});
    } finally {
      setImporting(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveMsg(null);
    try {
      const body = { LICHESS_USERNAME: username, STOCKFISH_DEPTH: depth };
      if (token) body.LICHESS_TOKEN = token;
      const res = await fetch("/api/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      setSaveMsg(data.note || "Saved");
    } catch {
      setSaveMsg("Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleRestart = async () => {
    setRestarting(true);
    try {
      await fetch("/api/restart", { method: "POST" });
    } catch {
      // Connection will drop during restart
    }
    // Poll until backend comes back
    const poll = setInterval(async () => {
      try {
        const res = await fetch("/health");
        if (res.ok) {
          clearInterval(poll);
          setRestarting(false);
          window.location.reload();
        }
      } catch {
        // Still restarting
      }
    }, 2000);
    // Give up after 30s
    setTimeout(() => {
      clearInterval(poll);
      setRestarting(false);
    }, 30000);
  };

  return (
    <div>
      <h2 style={{ marginTop: 0, marginBottom: 20 }}>Settings</h2>

      {/* Lichess Account */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ margin: "0 0 12px 0", fontSize: "0.95rem" }}>Lichess Account</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", width: 120 }}>
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              style={{
                flex: 1,
                maxWidth: 300,
                padding: "6px 8px",
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: 4,
                color: "var(--text-primary)",
                fontSize: "0.85rem",
                fontFamily: "inherit",
              }}
            />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", width: 120 }}>
              API Token
            </label>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder={config?.lichess_token_masked || "Enter token"}
              style={{
                flex: 1,
                maxWidth: 300,
                padding: "6px 8px",
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: 4,
                color: "var(--text-primary)",
                fontSize: "0.85rem",
                fontFamily: "inherit",
              }}
            />
          </div>
          {gameCount !== null && (
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", width: 120 }}>
                Games in DB
              </span>
              <span className="mono" style={{ fontWeight: 600 }}>{gameCount}</span>
            </div>
          )}
        </div>
      </div>

      {/* Engine Settings */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ margin: "0 0 12px 0", fontSize: "0.95rem" }}>Engine Settings</h3>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", width: 120 }}>
            Stockfish Depth
          </label>
          <input
            type="number"
            value={depth}
            onChange={(e) => setDepth(e.target.value)}
            min="10"
            max="30"
            style={{ width: 80 }}
          />
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
            Higher = more accurate, slower (default: 18)
          </span>
        </div>
      </div>

      {/* Save / Restart */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save Settings"}
          </button>
          <button
            onClick={handleRestart}
            disabled={restarting}
            style={{
              backgroundColor: restarting ? "var(--bg-elevated)" : "#d97706",
              color: "#fff",
              border: "none",
            }}
          >
            {restarting ? "Restarting..." : "Restart App"}
          </button>
          {saveMsg && (
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              {saveMsg}
            </span>
          )}
        </div>
      </div>

      {/* Game Import */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ margin: "0 0 12px 0", fontSize: "0.95rem" }}>Game Import</h3>
        <p style={{ margin: "0 0 12px 0", fontSize: "0.8rem", color: "var(--text-muted)" }}>
          Import rated games from your Lichess account. Duplicate games are automatically skipped.
        </p>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <select
            value={importCount}
            onChange={(e) => setImportCount(e.target.value)}
            disabled={importing}
            style={{
              padding: "6px 8px",
              background: "var(--bg-elevated)",
              border: "1px solid var(--border)",
              borderRadius: 4,
              color: "var(--text-primary)",
              fontSize: "0.85rem",
            }}
          >
            <option value="50">Last 50 games</option>
            <option value="100">Last 100 games</option>
            <option value="250">Last 250 games</option>
            <option value="500">Last 500 games</option>
            <option value="1000">Last 1000 games</option>
            <option value="all">All games</option>
          </select>
          <button onClick={handleImport} disabled={importing}>
            {importing ? "Importing..." : "Import from Lichess"}
          </button>
        </div>
        {importResult && (
          <div
            style={{
              marginTop: 12,
              padding: "8px 12px",
              background: "var(--bg-primary)",
              borderRadius: 4,
              fontSize: "0.8rem",
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}
          >
            <span style={{ color: "#4caf50" }}>{importResult.imported} imported</span>
            <span style={{ color: "var(--text-muted)" }}>{importResult.skipped} skipped</span>
            {importResult.errors > 0 && (
              <span style={{ color: "#f44336" }}>{importResult.errors} errors</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
