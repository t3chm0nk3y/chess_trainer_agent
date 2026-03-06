import { useEffect, useState } from "react";
import PatternCard from "../components/PatternCard";
import ProgressChart from "../components/ProgressChart";
import { getProgress, getProgressSummary, listPatterns, refreshPatterns } from "../api/client";

export default function ReportTab() {
  const [patterns, setPatterns] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [summary, setSummary] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    listPatterns().then((res) => setPatterns(res.patterns || []));
    getProgress().then((res) => setSnapshots(res.snapshots || []));
    getProgressSummary().then((res) => setSummary(res));
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refreshPatterns();
      const res = await listPatterns();
      setPatterns(res.patterns || []);
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div>
      {/* Summary stats */}
      {summary && (
        <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
          <StatCard label="Games Analyzed" value={summary.total_games} />
          <StatCard label="Overall Accuracy" value={`${summary.accuracy}%`} />
          <StatCard label="Active Patterns" value={summary.active_patterns} />
          <StatCard label="Total Moves" value={summary.total_moves} />
        </div>
      )}

      <ProgressChart snapshots={snapshots} />

      {/* Patterns */}
      <div style={{ marginTop: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h2 style={{ fontSize: "1.1rem" }}>Weakness Patterns</h2>
          <button className="btn btn-primary" onClick={handleRefresh} disabled={refreshing}>
            {refreshing ? "Refreshing..." : "Refresh Patterns"}
          </button>
        </div>
        {patterns.length === 0 ? (
          <div className="card" style={{ textAlign: "center", color: "var(--text-secondary)", padding: "2rem" }}>
            No patterns detected yet. Analyze at least 5 games to identify patterns.
          </div>
        ) : (
          patterns.map((p) => (
            <PatternCard
              key={p.id}
              pattern={p}
              expanded={expandedId === p.id}
              onToggle={() => setExpandedId(expandedId === p.id ? null : p.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div className="card" style={{ flex: 1, textAlign: "center" }}>
      <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--accent)" }}>
        {value}
      </div>
      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 4, textTransform: "uppercase" }}>
        {label}
      </div>
    </div>
  );
}
