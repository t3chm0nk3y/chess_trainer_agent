/**
 * Vertical evaluation bar (like Lichess).
 * Positive = white advantage, negative = black advantage.
 */
export default function EvalBar({ eval_cp = 0, height = 480 }) {
  // Clamp eval to [-1000, 1000] for display
  const clamped = Math.max(-1000, Math.min(1000, eval_cp));
  // Convert to percentage (50% = equal, 100% = white winning)
  const whitePercent = 50 + (clamped / 1000) * 50;

  const displayEval =
    Math.abs(eval_cp) >= 10000
      ? "M" + Math.ceil((10000 - Math.abs(eval_cp)) / 100)
      : (eval_cp / 100).toFixed(1);

  return (
    <div className="eval-bar" style={{ height, width: 28 }}>
      <div
        className="eval-bar-black"
        style={{ height: `${100 - whitePercent}%` }}
      />
      <div
        className="eval-bar-white"
        style={{ height: `${whitePercent}%` }}
      />
      <span className="eval-bar-label mono">{displayEval}</span>
      <style>{`
        .eval-bar {
          position: relative;
          display: flex;
          flex-direction: column;
          border-radius: 4px;
          overflow: hidden;
          border: 1px solid var(--border);
        }
        .eval-bar-black {
          background: #333;
          transition: height 0.3s ease;
        }
        .eval-bar-white {
          background: #f0f0f0;
          transition: height 0.3s ease;
        }
        .eval-bar-label {
          position: absolute;
          bottom: 4px;
          left: 50%;
          transform: translateX(-50%);
          font-size: 0.65rem;
          color: #333;
          font-weight: 700;
        }
      `}</style>
    </div>
  );
}
