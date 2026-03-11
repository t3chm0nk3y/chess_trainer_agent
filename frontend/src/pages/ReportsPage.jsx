import { useEffect, useState } from "react";
import { listReports, getReport, generateReports } from "../api/client";

const TYPE_LABELS = {
  player_profile: "Player Profile",
  opening: "Opening",
  pattern: "Pattern",
  monthly: "Monthly",
  phase: "Phase",
  game_condition: "Game Condition",
  weakness: "Weakness",
};

const TYPE_COLORS = {
  player_profile: "#4c6ef5",
  opening: "#7c3aed",
  pattern: "#dc2626",
  monthly: "#059669",
  phase: "#2563eb",
  game_condition: "#d97706",
  weakness: "#e91e63",
};

function TypeBadge({ type }) {
  return (
    <span
      className="badge"
      style={{ backgroundColor: TYPE_COLORS[type] || "#666", fontSize: "0.65rem" }}
    >
      {TYPE_LABELS[type] || type}
    </span>
  );
}

function CoverageBadge({ coverage }) {
  const colors = {
    full: "#4caf50",
    partial_annotations: "#ff9800",
    engine_only: "#2196f3",
  };
  const labels = {
    full: "Full",
    partial_annotations: "Partial",
    engine_only: "Engine Only",
  };
  return (
    <span
      className="badge"
      style={{ backgroundColor: colors[coverage] || "#666", fontSize: "0.6rem" }}
    >
      {labels[coverage] || coverage}
    </span>
  );
}

function ReportDetail({ data, reportType }) {
  if (!data) return null;

  if (reportType === "player_profile") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
          <StatBox label="Total Games" value={data.total_games} />
          <StatBox label="Wins" value={data.results?.wins} color="#4caf50" />
          <StatBox label="Losses" value={data.results?.losses} color="#f44336" />
          <StatBox label="Draws" value={data.results?.draws} color="#9e9e9e" />
        </div>
        {data.color_performance && (
          <div>
            <SectionLabel>Color Performance</SectionLabel>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {Object.entries(data.color_performance).map(([color, stats]) => (
                <div key={color} style={{ padding: 8, background: "var(--bg-primary)", borderRadius: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: "0.85rem", textTransform: "capitalize" }}>{color}</span>
                  <span className="mono" style={{ marginLeft: 8, fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    {stats.games} games — {stats.win_rate}% win rate
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
        {data.accuracy_by_phase && (
          <div>
            <SectionLabel>Accuracy by Phase</SectionLabel>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
              {Object.entries(data.accuracy_by_phase).map(([phase, stats]) => (
                <div key={phase} style={{ padding: 8, background: "var(--bg-primary)", borderRadius: 4 }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "capitalize" }}>{phase}</div>
                  <div className="mono" style={{ fontSize: "0.9rem", fontWeight: 600 }}>
                    {stats.avg_cp_loss} cp/move
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        {data.severity_distribution && (
          <div>
            <SectionLabel>Mistake Distribution</SectionLabel>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
              {[["inaccuracy", "var(--inaccuracy)"], ["mistake", "var(--mistake)"], ["blunder", "var(--blunder)"]].map(([sev, color]) => (
                <div key={sev} style={{ padding: 8, background: "var(--bg-primary)", borderRadius: 4 }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "capitalize" }}>{sev}s</div>
                  <div className="mono" style={{ fontSize: "0.9rem", fontWeight: 600, color }}>
                    {data.severity_distribution[sev] || 0}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        {data.top_openings?.length > 0 && (
          <div>
            <SectionLabel>Top Openings</SectionLabel>
            <KeyValueList items={data.top_openings.map(o => ({
              label: `${o.eco_code} ${o.opening_name}`,
              value: `${o.games} games — ${o.win_rate}% win`,
            }))} />
          </div>
        )}
      </div>
    );
  }

  // Generic JSON renderer for all other types
  return <JsonView data={data} />;
}

function StatBox({ label, value, color }) {
  return (
    <div style={{ padding: 8, background: "var(--bg-primary)", borderRadius: 4, textAlign: "center" }}>
      <div className="mono" style={{ fontSize: "1.2rem", fontWeight: 700, color: color || "var(--accent)" }}>
        {value ?? "—"}
      </div>
      <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>{label}</div>
    </div>
  );
}

function SectionLabel({ children }) {
  return (
    <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: 6 }}>
      {children}
    </div>
  );
}

function KeyValueList({ items }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {items.map((item, i) => (
        <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "4px 8px", background: "var(--bg-primary)", borderRadius: 4, fontSize: "0.8rem" }}>
          <span>{item.label}</span>
          <span className="mono" style={{ color: "var(--text-muted)" }}>{item.value}</span>
        </div>
      ))}
    </div>
  );
}

function JsonView({ data }) {
  if (data == null) return null;

  // Render objects as key-value sections
  if (typeof data === "object" && !Array.isArray(data)) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {Object.entries(data).map(([key, value]) => {
          const label = key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());

          // Simple values
          if (value === null || value === undefined) return null;
          if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
            return (
              <div key={key} style={{ display: "flex", justifyContent: "space-between", padding: "4px 8px", background: "var(--bg-primary)", borderRadius: 4, fontSize: "0.8rem" }}>
                <span style={{ color: "var(--text-muted)" }}>{label}</span>
                <span className="mono">{String(value)}</span>
              </div>
            );
          }

          // Arrays
          if (Array.isArray(value)) {
            if (value.length === 0) return null;
            return (
              <div key={key}>
                <SectionLabel>{label} ({value.length})</SectionLabel>
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  {value.slice(0, 10).map((item, i) => (
                    <div key={i} style={{ padding: "6px 8px", background: "var(--bg-primary)", borderRadius: 4, fontSize: "0.8rem" }}>
                      {typeof item === "object" ? (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                          {Object.entries(item).map(([k, v]) => (
                            <span key={k}>
                              <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>{k}: </span>
                              <span className="mono">{typeof v === "number" ? v : String(v ?? "—")}</span>
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="mono">{String(item)}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          }

          // Nested objects
          if (typeof value === "object") {
            return (
              <div key={key}>
                <SectionLabel>{label}</SectionLabel>
                <div style={{ paddingLeft: 8, borderLeft: "2px solid var(--border)" }}>
                  <JsonView data={value} />
                </div>
              </div>
            );
          }

          return null;
        })}
      </div>
    );
  }

  return <span className="mono" style={{ fontSize: "0.8rem" }}>{String(data)}</span>;
}

const TYPE_ORDER = ["player_profile", "monthly", "phase", "opening", "pattern", "game_condition", "weakness"];

export default function ReportsPage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [selectedType, setSelectedType] = useState("all");
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [dataLoading, setDataLoading] = useState(false);

  useEffect(() => {
    listReports()
      .then((r) => setReports(r.reports || []))
      .finally(() => setLoading(false));
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await generateReports();
      const r = await listReports();
      setReports(r.reports || []);
    } finally {
      setGenerating(false);
    }
  };

  const handleSelect = async (report) => {
    if (selectedReport?.report_key === report.report_key && selectedReport?.report_type === report.report_type) {
      setSelectedReport(null);
      setReportData(null);
      return;
    }
    setSelectedReport(report);
    setDataLoading(true);
    try {
      const full = await getReport(report.report_type, report.report_key);
      setReportData(full.data);
    } finally {
      setDataLoading(false);
    }
  };

  // Group by type
  const types = [...new Set(reports.map((r) => r.report_type))].sort(
    (a, b) => TYPE_ORDER.indexOf(a) - TYPE_ORDER.indexOf(b)
  );

  const filtered = selectedType === "all"
    ? reports
    : reports.filter((r) => r.report_type === selectedType);

  // Sort filtered within each type
  const sorted = [...filtered].sort((a, b) => {
    const typeA = TYPE_ORDER.indexOf(a.report_type);
    const typeB = TYPE_ORDER.indexOf(b.report_type);
    if (typeA !== typeB) return typeA - typeB;
    return a.title.localeCompare(b.title);
  });

  if (loading) return <p style={{ color: "var(--text-muted)" }}>Loading...</p>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>
          Reports{" "}
          <span style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>({reports.length})</span>
        </h2>
        <button onClick={handleGenerate} disabled={generating}>
          {generating ? "Generating..." : "Generate Reports"}
        </button>
      </div>

      {reports.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: 32 }}>
          <p style={{ color: "var(--text-muted)", margin: "0 0 12px 0" }}>
            No reports generated yet.
          </p>
          <button onClick={handleGenerate} disabled={generating}>
            {generating ? "Generating..." : "Generate Now"}
          </button>
        </div>
      ) : (
        <>
          {/* Type filter */}
          <div style={{ display: "flex", gap: 6, marginBottom: 16, flexWrap: "wrap" }}>
            <button
              onClick={() => setSelectedType("all")}
              style={{
                backgroundColor: selectedType === "all" ? "var(--accent)" : "var(--bg-elevated)",
                color: selectedType === "all" ? "#fff" : "var(--text-primary)",
                border: "none", padding: "4px 12px", borderRadius: 4, cursor: "pointer", fontSize: "0.8rem",
              }}
            >
              All ({reports.length})
            </button>
            {types.map((type) => {
              const count = reports.filter((r) => r.report_type === type).length;
              return (
                <button
                  key={type}
                  onClick={() => setSelectedType(type)}
                  style={{
                    backgroundColor: selectedType === type ? TYPE_COLORS[type] || "var(--accent)" : "var(--bg-elevated)",
                    color: selectedType === type ? "#fff" : "var(--text-primary)",
                    border: "none", padding: "4px 12px", borderRadius: 4, cursor: "pointer", fontSize: "0.8rem",
                  }}
                >
                  {TYPE_LABELS[type] || type} ({count})
                </button>
              );
            })}
          </div>

          {/* Report list + detail */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            {/* Left: list */}
            <div className="card" style={{ padding: 0, overflow: "hidden", alignSelf: "start", maxHeight: 600 }}>
              <div style={{ overflowY: "auto", maxHeight: 600 }}>
                {sorted.map((r) => {
                  const isActive = selectedReport?.report_type === r.report_type && selectedReport?.report_key === r.report_key;
                  return (
                    <div
                      key={`${r.report_type}-${r.report_key}`}
                      onClick={() => handleSelect(r)}
                      className="hover-row"
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "8px 12px",
                        cursor: "pointer",
                        background: isActive ? "var(--bg-elevated)" : "transparent",
                        borderLeft: isActive ? "3px solid var(--accent)" : "3px solid transparent",
                      }}
                    >
                      <TypeBadge type={r.report_type} />
                      <span style={{ fontSize: "0.85rem", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {r.title}
                      </span>
                      <CoverageBadge coverage={r.data_coverage} />
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right: detail */}
            <div className="card" style={{ alignSelf: "start" }}>
              {dataLoading ? (
                <p style={{ color: "var(--text-muted)", margin: 0 }}>Loading...</p>
              ) : selectedReport && reportData ? (
                <div>
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <TypeBadge type={selectedReport.report_type} />
                      <CoverageBadge coverage={selectedReport.data_coverage} />
                    </div>
                    <h3 style={{ margin: "4px 0 0 0" }}>{selectedReport.title}</h3>
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                      Generated: {selectedReport.generated_at?.slice(0, 19).replace("T", " ")}
                    </div>
                  </div>
                  <ReportDetail data={reportData} reportType={selectedReport.report_type} />
                </div>
              ) : (
                <p style={{ color: "var(--text-muted)", margin: 0 }}>
                  Select a report to view details.
                </p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
