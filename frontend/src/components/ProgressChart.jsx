import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/**
 * Accuracy over time line chart.
 */
export default function ProgressChart({ snapshots = [] }) {
  const data = snapshots.map((s) => ({
    date: s.date,
    accuracy: s.avg_accuracy,
    games: s.total_games,
  }));

  if (!data.length) {
    return (
      <div className="card" style={{ padding: "2rem", textAlign: "center", color: "var(--text-secondary)" }}>
        No progress data yet. Analyze some games to see your trend.
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: "1rem" }}>
      <h3 style={{ fontSize: "0.9rem", marginBottom: 12, color: "var(--text-secondary)" }}>
        Accuracy Over Time
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="date" stroke="var(--text-secondary)" fontSize={11} />
          <YAxis domain={[0, 100]} stroke="var(--text-secondary)" fontSize={11} />
          <Tooltip
            contentStyle={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: 4,
            }}
          />
          <Line
            type="monotone"
            dataKey="accuracy"
            stroke="var(--accent)"
            strokeWidth={2}
            dot={{ fill: "var(--accent)", r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
