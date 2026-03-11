/**
 * Scrollable move list with severity indicators.
 * Expects moves as array of { move_number, color, san, mistake_severity, ply }
 */
export default function MoveList({ moves = [], currentPly = 0, onSelectPly }) {
  const pairs = [];
  for (let i = 0; i < moves.length; i += 2) {
    pairs.push({
      number: moves[i].move_number,
      white: moves[i],
      black: moves[i + 1] || null,
    });
  }

  return (
    <div className="card" style={{ maxHeight: 480, overflowY: "auto", padding: 0 }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <tbody>
          {pairs.map((pair) => (
            <tr key={pair.number}>
              <td
                className="mono"
                style={{
                  color: "var(--text-muted)",
                  width: 36,
                  padding: "2px 6px",
                  fontSize: "0.75rem",
                }}
              >
                {pair.number}.
              </td>
              <MoveCell
                move={pair.white}
                isActive={pair.white?.ply === currentPly}
                onClick={() => onSelectPly?.(pair.white.ply)}
              />
              {pair.black ? (
                <MoveCell
                  move={pair.black}
                  isActive={pair.black?.ply === currentPly}
                  onClick={() => onSelectPly?.(pair.black.ply)}
                />
              ) : (
                <td />
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MoveCell({ move, isActive, onClick }) {
  if (!move) return <td />;

  const severityColor = {
    inaccuracy: "var(--inaccuracy)",
    mistake: "var(--mistake)",
    blunder: "var(--blunder)",
  }[move.mistake_severity];

  return (
    <td
      className="mono"
      onClick={onClick}
      style={{
        padding: "2px 8px",
        cursor: "pointer",
        fontSize: "0.8rem",
        backgroundColor: isActive ? "var(--bg-elevated)" : "transparent",
        borderLeft: severityColor
          ? `3px solid ${severityColor}`
          : "3px solid transparent",
      }}
    >
      {move.san}
    </td>
  );
}
