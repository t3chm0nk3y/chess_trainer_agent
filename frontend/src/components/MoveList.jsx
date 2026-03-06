/**
 * Scrollable move list with classification badges.
 */
export default function MoveList({ moves = [], currentPly = 0, onSelectPly }) {
  // Group moves into pairs (white + black)
  const pairs = [];
  for (let i = 0; i < moves.length; i += 2) {
    pairs.push({
      number: Math.floor(i / 2) + 1,
      white: moves[i],
      black: moves[i + 1] || null,
    });
  }

  return (
    <div className="move-list card" style={{ maxHeight: 480, overflowY: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <tbody>
          {pairs.map((pair) => (
            <tr key={pair.number}>
              <td className="mono" style={{ color: "var(--text-secondary)", width: 36, padding: "2px 4px" }}>
                {pair.number}.
              </td>
              <MoveCell
                move={pair.white}
                isActive={pair.white?.ply + 1 === currentPly}
                onClick={() => onSelectPly?.(pair.white.ply + 1)}
              />
              {pair.black && (
                <MoveCell
                  move={pair.black}
                  isActive={pair.black?.ply + 1 === currentPly}
                  onClick={() => onSelectPly?.(pair.black.ply + 1)}
                />
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

  const classColor = {
    best: "var(--best)",
    good: "var(--good)",
    inaccuracy: "var(--inaccuracy)",
    mistake: "var(--mistake)",
    blunder: "var(--blunder)",
  }[move.classification];

  return (
    <td
      className="mono"
      onClick={onClick}
      style={{
        padding: "2px 8px",
        cursor: "pointer",
        borderRadius: 3,
        backgroundColor: isActive ? "var(--bg-secondary)" : "transparent",
        borderLeft: classColor ? `3px solid ${classColor}` : "3px solid transparent",
      }}
    >
      {move.san}
    </td>
  );
}
