/**
 * Pattern display card with severity bar and trend indicator.
 */
export default function PatternCard({ pattern, expanded = false, onToggle }) {
  const severityColor =
    pattern.severity_score > 70
      ? "var(--error)"
      : pattern.severity_score > 40
        ? "var(--warning)"
        : "var(--success)";

  return (
    <div className="card pattern-card" onClick={onToggle} style={{ cursor: "pointer", marginBottom: "0.75rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h3 style={{ fontSize: "0.95rem", marginBottom: 4 }}>{pattern.label}</h3>
          <span className="badge" style={{ backgroundColor: "var(--bg-secondary)", color: "var(--text-secondary)" }}>
            {pattern.category}
          </span>
          <span style={{ marginLeft: 8, fontSize: "0.8rem", color: "var(--text-secondary)" }}>
            {pattern.frequency} games
          </span>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: "1.25rem", fontWeight: 700, color: severityColor }}>
            {pattern.severity_score}
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>severity</div>
        </div>
      </div>

      {/* Severity bar */}
      <div
        style={{
          marginTop: 8,
          height: 4,
          borderRadius: 2,
          backgroundColor: "var(--bg-secondary)",
        }}
      >
        <div
          style={{
            width: `${pattern.severity_score}%`,
            height: "100%",
            borderRadius: 2,
            backgroundColor: severityColor,
            transition: "width 0.3s ease",
          }}
        />
      </div>

      {expanded && (
        <div style={{ marginTop: 12, fontSize: "0.85rem" }}>
          <p style={{ color: "var(--text-secondary)", marginBottom: 8 }}>
            {pattern.description}
          </p>
          {pattern.training_recommendation && (
            <div
              style={{
                padding: "0.5rem 0.75rem",
                backgroundColor: "var(--bg-secondary)",
                borderRadius: 6,
                borderLeft: "3px solid var(--accent)",
              }}
            >
              <strong style={{ fontSize: "0.75rem", color: "var(--accent)" }}>
                Training recommendation
              </strong>
              <p style={{ marginTop: 4 }}>{pattern.training_recommendation}</p>
            </div>
          )}
        </div>
      )}

      <style>{`
        .pattern-card:hover {
          border-color: var(--accent);
        }
      `}</style>
    </div>
  );
}
