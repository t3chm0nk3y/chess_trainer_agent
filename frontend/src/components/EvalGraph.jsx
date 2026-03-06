import {
  Area,
  AreaChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/**
 * Sparkline eval chart showing evaluation over the course of a game.
 */
export default function EvalGraph({ moves = [], currentPly = 0, onClickPly }) {
  const data = moves.map((m, i) => ({
    ply: i + 1,
    eval: m.engine_eval_after != null ? m.engine_eval_after / 100 : 0,
    classification: m.classification,
  }));

  return (
    <div className="eval-graph card" style={{ padding: "0.75rem" }}>
      <ResponsiveContainer width="100%" height={80}>
        <AreaChart
          data={data}
          onClick={(e) => e?.activeLabel && onClickPly?.(e.activeLabel)}
        >
          <defs>
            <linearGradient id="evalGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4caf50" stopOpacity={0.4} />
              <stop offset="50%" stopColor="#4caf50" stopOpacity={0} />
              <stop offset="50%" stopColor="#f44336" stopOpacity={0} />
              <stop offset="100%" stopColor="#f44336" stopOpacity={0.4} />
            </linearGradient>
          </defs>
          <XAxis dataKey="ply" hide />
          <YAxis domain={[-5, 5]} hide />
          <ReferenceLine y={0} stroke="var(--border)" strokeDasharray="3 3" />
          <Tooltip
            contentStyle={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: 4,
              fontSize: "0.75rem",
            }}
            formatter={(val) => [`${val > 0 ? "+" : ""}${val.toFixed(1)}`, "Eval"]}
            labelFormatter={(ply) => `Move ${Math.ceil(ply / 2)}`}
          />
          <Area
            type="monotone"
            dataKey="eval"
            stroke="var(--accent)"
            fill="url(#evalGrad)"
            strokeWidth={1.5}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
