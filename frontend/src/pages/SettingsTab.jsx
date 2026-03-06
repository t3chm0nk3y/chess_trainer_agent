import { useEffect, useState } from "react";
import AnalysisSummary from "../components/AnalysisSummary";
import GameImporter from "../components/GameImporter";
import WorkflowProgress from "../components/WorkflowProgress";
import useAnalysis from "../hooks/useAnalysis";
import { listGames } from "../api/client";

export default function SettingsTab() {
  const [section, setSection] = useState("import");
  const [jobId, setJobId] = useState(null);
  const [importResult, setImportResult] = useState(null);
  const [recentImports, setRecentImports] = useState([]);
  const { status, error, isLoading } = useAnalysis(jobId);

  const handleImportComplete = (result) => {
    setImportResult(result);
    if (result?.job_id) {
      setJobId(result.job_id);
    }
    // Refresh recent imports
    listGames({ limit: 5 }).then((res) => setRecentImports(res.games || []));
  };

  useEffect(() => {
    listGames({ limit: 5 }).then((res) => setRecentImports(res.games || []));
  }, []);

  return (
    <div style={{ maxWidth: 700 }}>
      {/* Section tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 24 }}>
        {[
          { key: "import", label: "Import Games" },
          { key: "account", label: "Account" },
        ].map((s) => (
          <button
            key={s.key}
            className={`btn ${section === s.key ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setSection(s.key)}
          >
            {s.label}
          </button>
        ))}
      </div>

      {section === "import" && (
        <>
          <GameImporter onImportComplete={handleImportComplete} />

          {isLoading && status && <WorkflowProgress run={status} />}

          {error && (
            <div
              className="card"
              style={{ marginTop: 12, color: "var(--error)", borderColor: "var(--error)" }}
            >
              Error: {error}
            </div>
          )}

          {status?.status === "completed" && (
            <AnalysisSummary game={importResult} moves={[]} matchedPatterns={[]} />
          )}

          {/* Recent imports */}
          {recentImports.length > 0 && (
            <div style={{ marginTop: 24 }}>
              <h3 style={{ fontSize: "0.9rem", color: "var(--text-secondary)", marginBottom: 8 }}>
                Recently Imported
              </h3>
              {recentImports.map((g) => (
                <div
                  key={g.id}
                  className="card"
                  style={{ marginBottom: 6, padding: "0.5rem 0.75rem", fontSize: "0.85rem" }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>
                      <strong>{g.white}</strong> vs <strong>{g.black}</strong>
                    </span>
                    <span style={{ color: "var(--text-secondary)" }}>{g.date_played || "?"}</span>
                  </div>
                  <div style={{ display: "flex", gap: 8, marginTop: 4, fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    <span>{g.result}</span>
                    <span>{g.source}</span>
                    <span
                      className="badge"
                      style={{
                        fontSize: "0.65rem",
                        backgroundColor:
                          g.analysis_status === "analyzed"
                            ? "var(--success)"
                            : g.analysis_status === "error"
                              ? "var(--error)"
                              : "var(--bg-secondary)",
                        color: g.analysis_status === "pending" ? "var(--text-secondary)" : "#fff",
                      }}
                    >
                      {g.analysis_status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {section === "account" && (
        <div className="card" style={{ color: "var(--text-secondary)" }}>
          <h3 style={{ fontSize: "0.95rem", marginBottom: 12, color: "var(--text-primary)" }}>
            Account Settings
          </h3>
          <p style={{ fontSize: "0.85rem" }}>
            API keys and account connections are configured via the <code>.env</code> file.
          </p>
          <div style={{ marginTop: 12, fontSize: "0.85rem" }}>
            <div style={{ marginBottom: 8 }}>
              <strong>Anthropic API</strong>: {" "}
              <span style={{ color: "var(--success)" }}>Configured</span>
            </div>
            <div>
              <strong>Lichess Token</strong>: {" "}
              <span style={{ color: "var(--success)" }}>Configured</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
