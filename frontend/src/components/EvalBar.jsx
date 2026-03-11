/**
 * Vertical evaluation bar (like Lichess).
 * Positive = white advantage, negative = black advantage.
 */
export default function EvalBar({ eval_cp = 0, height = 360 }) {
  const clamped = Math.max(-1000, Math.min(1000, eval_cp));
  const whitePercent = 50 + (clamped / 1000) * 50;

  const displayEval =
    Math.abs(eval_cp) >= 10000
      ? "M" + Math.ceil((10000 - Math.abs(eval_cp)) / 100)
      : (eval_cp / 100).toFixed(1);

  return (
    <div style={{
      position: "relative",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      border: "1px solid var(--border)",
      height,
      width: 28,
      borderRadius: 2,
    }}>
      <div
        style={{
          background: "#333",
          height: `${100 - whitePercent}%`,
          transition: "height 0.3s ease",
        }}
      />
      <div
        style={{
          background: "#f0f0f0",
          height: `${whitePercent}%`,
          transition: "height 0.3s ease",
        }}
      />
      <span
        className="mono"
        style={{
          position: "absolute",
          bottom: 4,
          left: "50%",
          transform: "translateX(-50%)",
          fontSize: "0.65rem",
          color: "#333",
          fontWeight: 700,
        }}
      >
        {displayEval}
      </span>
    </div>
  );
}
