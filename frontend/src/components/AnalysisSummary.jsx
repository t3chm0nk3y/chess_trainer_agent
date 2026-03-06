/**
 * Post-analysis results summary card.
 */
export default function AnalysisSummary({ game, moves, matchedPatterns }) {
  if (!game) return null;

  const total = moves?.length || 0;
  const classifications = {};
  (moves || []).forEach((m) => {
    if (m.classification) {
      classifications[m.classification] = (classifications[m.classification] || 0) + 1;
    }
  });

  const accuracy =
    total > 0
      ? (((classifications.best || 0) + (classifications.good || 0)) / total) * 100
      : 0;

  return (
    <div className="card" style={{ marginTop: 12 }}>
      <h3 style={{ fontSize: "0.95rem", marginBottom: 12 }}>Analysis Summary</h3>

      <div style={{ display: "flex", gap: 24, marginBottom: 16 }}>
        <StatBox label="Result" value={game.result} />
        <StatBox label="Accuracy" value={`${accuracy.toFixed(1)}%`} />
        <StatBox label="Moves" value={total} />
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        {["best", "good", "inaccuracy", "mistake", "blunder"].map((cls) => (
          <span key={cls} className={`badge badge-${cls}`}>
            {cls}: {classifications[cls] || 0}
          </span>
        ))}
      </div>

      {matchedPatterns && matchedPatterns.length > 0 && (
        <div>
          <h4 style={{ fontSize: "0.85rem", marginBottom: 8, color: "var(--text-secondary)" }}>
            Matched Patterns
          </h4>
          {matchedPatterns.map((mp, i) => (
            <div
              key={i}
              style={{
                padding: "0.5rem",
                marginBottom: 4,
                borderRadius: 4,
                backgroundColor: "var(--bg-secondary)",
                fontSize: "0.85rem",
              }}
            >
              <strong>{mp.pattern_label}</strong>
              {mp.notes && (
                <span style={{ color: "var(--text-secondary)", marginLeft: 8 }}>
                  {mp.notes}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatBox({ label, value }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--accent)" }}>
        {value}
      </div>
      <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)", textTransform: "uppercase" }}>
        {label}
      </div>
    </div>
  );
}
