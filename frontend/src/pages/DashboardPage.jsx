import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

function ResultBadge({ result }) {
  const colors = { win: "#4caf50", loss: "#f44336", draw: "#9e9e9e" };
  return (
    <span className="badge" style={{ backgroundColor: colors[result] || "#666" }}>
      {result}
    </span>
  );
}

function PipelineBar({ label, counts, total }) {
  const complete = counts.complete || 0;
  const running = counts.running || 0;
  const failed = counts.failed || 0;
  const pending = total - complete - running - failed;
  const pct = total > 0 ? Math.round((complete / total) * 100) : 0;

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>{label}</span>
        <span className="mono" style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
          {complete}/{total} ({pct}%)
        </span>
      </div>
      <div
        style={{
          height: 8,
          borderRadius: 4,
          background: "var(--bg-primary)",
          overflow: "hidden",
          display: "flex",
        }}
      >
        {complete > 0 && (
          <div
            style={{
              width: `${(complete / total) * 100}%`,
              background: "#4caf50",
              transition: "width 0.5s ease",
            }}
          />
        )}
        {running > 0 && (
          <div
            style={{
              width: `${(running / total) * 100}%`,
              background: "#2196f3",
            }}
          />
        )}
        {failed > 0 && (
          <div
            style={{
              width: `${(failed / total) * 100}%`,
              background: "#f44336",
            }}
          />
        )}
      </div>
      <div
        style={{
          display: "flex",
          gap: 12,
          marginTop: 4,
          fontSize: "0.7rem",
          color: "var(--text-muted)",
        }}
      >
        {complete > 0 && (
          <span>
            <span style={{ color: "#4caf50" }}>●</span> {complete} complete
          </span>
        )}
        {running > 0 && (
          <span>
            <span style={{ color: "#2196f3" }}>●</span> {running} running
          </span>
        )}
        {failed > 0 && (
          <span>
            <span style={{ color: "#f44336" }}>●</span> {failed} failed
          </span>
        )}
        {pending > 0 && (
          <span>
            <span style={{ color: "var(--text-muted)" }}>●</span> {pending} pending
          </span>
        )}
      </div>
    </div>
  );
}

function PhaseBadge({ phase }) {
  const colors = {
    opening: "#7c3aed",
    middlegame: "#2563eb",
    endgame: "#059669",
  };
  return (
    <span
      className="badge"
      style={{ backgroundColor: colors[phase] || "#666", fontSize: "0.65rem" }}
    >
      {phase}
    </span>
  );
}

function AxisBadge({ axis }) {
  const colors = { tactical: "#dc2626", strategic: "#d97706" };
  return (
    <span
      className="badge"
      style={{ backgroundColor: colors[axis] || "#666", fontSize: "0.65rem" }}
    >
      {axis}
    </span>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetch("/api/dashboard")
      .then((r) => r.json())
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p style={{ color: "var(--text-muted)" }}>Loading...</p>;
  if (!data) return <p>Failed to load dashboard</p>;

  const { total_games, pipeline, recent_games, top_patterns, openings_computed } = data;

  return (
    <div>
      <h2 style={{ marginTop: 0, marginBottom: 20 }}>Dashboard</h2>

      {/* Stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 20 }}>
        {[
          { label: "Total Games", value: total_games },
          { label: "Analyzed", value: pipeline.engine?.complete || 0 },
          { label: "Annotated", value: pipeline.annotation?.complete || 0 },
          { label: "Openings Tracked", value: openings_computed },
        ].map((s) => (
          <div
            key={s.label}
            className="card"
            style={{ textAlign: "center", padding: "12px 8px" }}
          >
            <div className="mono" style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--accent)" }}>
              {s.value}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>
              {s.label}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* Left column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Recent Games */}
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h3 style={{ margin: 0, fontSize: "0.95rem" }}>Recent Games</h3>
              <button
                style={{ fontSize: "0.75rem", padding: "3px 10px" }}
                onClick={() => navigate("/games")}
              >
                View all
              </button>
            </div>
            <div style={{ display: "flex", flexDirection: "column" }}>
              {recent_games.map((g) => (
                <div
                  key={g.id}
                  onClick={() => navigate(`/games/${g.id}`)}
                  className="hover-row"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "6px 8px",
                    cursor: "pointer",
                    borderRadius: 4,
                  }}
                >
                  <ResultBadge result={g.result} />
                  <span style={{ fontSize: "0.85rem", fontWeight: 500, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {g.opponent_username || "Unknown"}
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 140 }}>
                    {g.opening_name || g.eco_code || ""}
                  </span>
                  <span className="mono" style={{ fontSize: "0.7rem", color: "var(--text-muted)", flexShrink: 0 }}>
                    {g.played_at?.slice(0, 10)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Pipeline Status */}
          <div className="card">
            <h3 style={{ margin: "0 0 12px 0", fontSize: "0.95rem" }}>Pipeline Status</h3>
            <PipelineBar label="Engine Analysis" counts={pipeline.engine || {}} total={total_games} />
            <PipelineBar label="AI Annotation" counts={pipeline.annotation || {}} total={total_games} />
            <PipelineBar label="Condition Detection" counts={pipeline.condition || {}} total={total_games} />
          </div>
        </div>

        {/* Right column: Top Patterns */}
        <div className="card" style={{ alignSelf: "start" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ margin: 0, fontSize: "0.95rem" }}>Top Recurring Mistakes</h3>
            <button
              style={{ fontSize: "0.75rem", padding: "3px 10px" }}
              onClick={() => navigate("/patterns")}
            >
              View all
            </button>
          </div>
          {top_patterns.length === 0 ? (
            <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "0.85rem" }}>
              No patterns detected yet. Run annotation pipeline to identify mistakes.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column" }}>
              {top_patterns.map((p, i) => (
                <div
                  key={p.id}
                  className="hover-row"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "6px 8px",
                    borderRadius: 4,
                    cursor: "pointer",
                  }}
                  onClick={() => navigate(`/patterns`)}
                >
                  <span
                    className="mono"
                    style={{
                      width: 20,
                      fontSize: "0.75rem",
                      color: "var(--text-muted)",
                      textAlign: "right",
                      flexShrink: 0,
                    }}
                  >
                    {i + 1}.
                  </span>
                  <span style={{ fontSize: "0.85rem", fontWeight: 500, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {p.name}
                  </span>
                  <PhaseBadge phase={p.phase} />
                  <AxisBadge axis={p.axis} />
                  <span
                    className="mono"
                    style={{
                      fontSize: "0.8rem",
                      fontWeight: 700,
                      color: "var(--accent)",
                      flexShrink: 0,
                      minWidth: 24,
                      textAlign: "right",
                    }}
                  >
                    {p.frequency}x
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
