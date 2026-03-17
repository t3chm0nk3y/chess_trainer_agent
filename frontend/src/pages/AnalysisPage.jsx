import { useEffect, useState, useCallback } from "react";
import { listGames, getGame, getGameMistakes } from "../api/client";
import ChessBoard from "../components/ChessBoard";
import EvalBar from "../components/EvalBar";

function ResultBadge({ result }) {
  const colors = { win: "#4caf50", loss: "#f44336", draw: "#9e9e9e" };
  return (
    <span className="badge" style={{ backgroundColor: colors[result] || "#666" }}>
      {result}
    </span>
  );
}

function SeverityBadge({ severity }) {
  const colors = {
    inaccuracy: "var(--inaccuracy)",
    mistake: "var(--mistake)",
    blunder: "var(--blunder)",
  };
  return (
    <span className="badge" style={{ backgroundColor: colors[severity] || "#666" }}>
      {severity}
    </span>
  );
}

function PhaseBadge({ phase }) {
  const colors = { opening: "#7c3aed", middlegame: "#2563eb", endgame: "#059669" };
  return (
    <span
      className="badge"
      style={{ backgroundColor: colors[phase] || "#666", fontSize: "0.65rem" }}
    >
      {phase}
    </span>
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
        backgroundColor: isActive ? "var(--accent)" : "transparent",
        color: isActive ? "#fff" : "var(--text-primary)",
        borderLeft: severityColor
          ? `3px solid ${severityColor}`
          : "3px solid transparent",
        borderRadius: isActive ? 2 : 0,
      }}
    >
      {move.san}
    </td>
  );
}

export default function AnalysisPage() {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);
  const [game, setGame] = useState(null);
  const [mistakes, setMistakes] = useState([]);
  const [currentPly, setCurrentPly] = useState(0);
  const [gameLoading, setGameLoading] = useState(false);
  const [username, setUsername] = useState("");

  // Load game list
  useEffect(() => {
    fetch("/api/config").then((r) => r.json()).then((c) => setUsername(c.username)).catch(() => {});
    listGames({ limit: 50, offset: 0 })
      .then((data) => setGames(data.games))
      .finally(() => setLoading(false));
  }, []);

  // Load selected game
  const selectGame = useCallback(async (id) => {
    if (id === selectedId) return;
    setSelectedId(id);
    setGameLoading(true);
    setCurrentPly(0);
    try {
      const [g, m] = await Promise.all([getGame(id), getGameMistakes(id)]);
      setGame(g);
      setMistakes(m.mistakes || []);
    } finally {
      setGameLoading(false);
    }
  }, [selectedId]);

  // Keyboard navigation
  useEffect(() => {
    const handler = (e) => {
      if (!game) return;
      const moves = game.moves || [];
      if (e.key === "ArrowRight" && currentPly < moves.length) {
        setCurrentPly((p) => p + 1);
      } else if (e.key === "ArrowLeft" && currentPly > 0) {
        setCurrentPly((p) => p - 1);
      } else if (e.key === "Home") {
        setCurrentPly(0);
      } else if (e.key === "End") {
        setCurrentPly(moves.length);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [game, currentPly]);

  // Sort moves into game order: by move_number, white before black
  const moves = (game?.moves || [])
    .slice()
    .sort((a, b) => {
      if (a.move_number !== b.move_number) return a.move_number - b.move_number;
      return a.color === "white" ? -1 : 1;
    })
    .map((m, i) => ({ ...m, ply: i + 1 }));
  const currentFen =
    currentPly > 0 && moves[currentPly - 1]
      ? moves[currentPly - 1].fen_after
      : "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
  const currentMove = currentPly > 0 ? moves[currentPly - 1] : null;

  // Build move pairs for the compact move list
  const movePairs = [];
  for (let i = 0; i < moves.length; i += 2) {
    movePairs.push({
      number: moves[i].move_number,
      white: moves[i],
      black: moves[i + 1] || null,
    });
  }

  // Find mistake detail for current move
  const currentMistake = currentMove?.mistake_severity
    ? mistakes.find(
        (m) => m.move_number === currentMove.move_number && m.color === currentMove.color
      )
    : null;

  return (
    <div>
      <h2 style={{ marginTop: 0, marginBottom: 16 }}>Analysis</h2>

      <div style={{ display: "grid", gridTemplateColumns: "396px 1fr", gap: 20 }}>
        {/* Left: Board */}
        <div>
          {game && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, paddingLeft: 36 }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>
                {game.opponent_username || "Unknown"}
              </span>
              <span
                className="badge"
                style={{
                  backgroundColor: game.player_color === "white" ? "#333" : "#f0f0f0",
                  color: game.player_color === "white" ? "#f0f0f0" : "#333",
                }}
              >
                {game.player_color === "white" ? "black" : "white"}
              </span>
            </div>
          )}
          <div style={{ display: "flex", gap: 8 }}>
            <EvalBar eval_cp={currentMove?.cp_eval_after ?? 0} height={360} />
            <ChessBoard
              fen={currentFen}
              boardWidth={360}
              orientation={game?.player_color || "white"}
            />
          </div>
          {game && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4, paddingLeft: 36 }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--accent)" }}>
                {username || "You"}
              </span>
              <span
                className="badge"
                style={{
                  backgroundColor: game.player_color === "white" ? "#f0f0f0" : "#333",
                  color: game.player_color === "white" ? "#333" : "#f0f0f0",
                }}
              >
                {game.player_color}
              </span>
            </div>
          )}
          {/* Nav buttons */}
          {game && (
            <div style={{ display: "flex", gap: 4, marginTop: 8, paddingLeft: 36 }}>
              <button style={{ padding: "4px 10px", fontSize: "0.8rem" }} onClick={() => setCurrentPly(0)} disabled={currentPly === 0}>
                ⏮
              </button>
              <button style={{ padding: "4px 10px", fontSize: "0.8rem" }} onClick={() => setCurrentPly(Math.max(0, currentPly - 1))} disabled={currentPly === 0}>
                ◀
              </button>
              <button style={{ padding: "4px 10px", fontSize: "0.8rem" }} onClick={() => setCurrentPly(Math.min(moves.length, currentPly + 1))} disabled={currentPly >= moves.length}>
                ▶
              </button>
              <button style={{ padding: "4px 10px", fontSize: "0.8rem" }} onClick={() => setCurrentPly(moves.length)} disabled={currentPly >= moves.length}>
                ⏭
              </button>
              <span className="mono" style={{ padding: "4px 8px", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                {currentPly}/{moves.length}
              </span>
            </div>
          )}
        </div>

        {/* Right: Game selector */}
        <div className="card" style={{ padding: 0, overflow: "hidden", alignSelf: "start", maxHeight: 460 }}>
          <div style={{ padding: "10px 12px", borderBottom: "1px solid var(--border)", fontSize: "0.8rem", fontWeight: 600, color: "var(--text-muted)" }}>
            Recent Games ({games.length})
          </div>
          {loading ? (
            <p style={{ padding: 12, color: "var(--text-muted)" }}>Loading...</p>
          ) : (
            <div style={{ overflowY: "auto", maxHeight: 416 }}>
              {games.map((g) => (
                <div
                  key={g.id}
                  onClick={() => selectGame(g.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "6px 12px",
                    cursor: "pointer",
                    background: g.id === selectedId ? "var(--bg-elevated)" : "transparent",
                    borderLeft: g.id === selectedId ? "3px solid var(--accent)" : "3px solid transparent",
                  }}
                  className="hover-row"
                >
                  <ResultBadge result={g.result} />
                  <span style={{ fontSize: "0.8rem", fontWeight: 500, minWidth: 80, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {g.opponent_username || "Unknown"}
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {g.opening_name || g.eco_code || ""}
                  </span>
                  <span className="mono" style={{ fontSize: "0.65rem", color: "var(--text-muted)", flexShrink: 0 }}>
                    {g.played_at?.slice(0, 10)}
                  </span>
                  {g.annotation_status === "complete" && (
                    <span style={{ color: "#4caf50", fontSize: "0.7rem", flexShrink: 0 }} title="Annotated">✓</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom: Move list + annotation detail */}
      {game && !gameLoading && (
        <div style={{ marginTop: 20, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          {/* Move list */}
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <div style={{ padding: "10px 12px", borderBottom: "1px solid var(--border)", fontSize: "0.8rem", fontWeight: 600, color: "var(--text-muted)" }}>
              Moves — {game.opening_name || game.eco_code || "Unknown Opening"}
              {game.variation_name && (
                <span style={{ fontWeight: 400, fontStyle: "italic" }}> · {game.variation_name}</span>
              )}
            </div>
            <div style={{ maxHeight: 360, overflowY: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <tbody>
                  {movePairs.map((pair) => (
                    <tr key={pair.number}>
                      <td
                        className="mono"
                        style={{ color: "var(--text-muted)", width: 36, padding: "2px 6px", fontSize: "0.75rem" }}
                      >
                        {pair.number}.
                      </td>
                      <MoveCell
                        move={pair.white}
                        isActive={pair.white?.ply === currentPly}
                        onClick={() => setCurrentPly(pair.white.ply)}
                      />
                      {pair.black ? (
                        <MoveCell
                          move={pair.black}
                          isActive={pair.black?.ply === currentPly}
                          onClick={() => setCurrentPly(pair.black.ply)}
                        />
                      ) : (
                        <td />
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Annotation detail */}
          <div className="card">
            <div style={{ marginBottom: 12, fontSize: "0.8rem", fontWeight: 600, color: "var(--text-muted)" }}>
              Move Detail
            </div>
            {currentMove ? (
              <div>
                {/* Move header */}
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                  <span className="mono" style={{ fontSize: "1.1rem", fontWeight: 700 }}>
                    {currentMove.move_number}.{currentMove.color === "black" ? ".." : ""} {currentMove.san}
                  </span>
                  {currentMove.mistake_severity && (
                    <SeverityBadge severity={currentMove.mistake_severity} />
                  )}
                  <PhaseBadge phase={currentMove.phase} />
                </div>

                {/* Eval info */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, marginBottom: 16 }}>
                  <div style={{ padding: 8, background: "var(--bg-primary)", borderRadius: 4 }}>
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: 2 }}>Eval Before</div>
                    <div className="mono" style={{ fontSize: "0.9rem", fontWeight: 600 }}>
                      {currentMove.cp_eval_before != null ? (currentMove.cp_eval_before / 100).toFixed(1) : "—"}
                    </div>
                  </div>
                  <div style={{ padding: 8, background: "var(--bg-primary)", borderRadius: 4 }}>
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: 2 }}>Eval After</div>
                    <div className="mono" style={{ fontSize: "0.9rem", fontWeight: 600 }}>
                      {currentMove.cp_eval_after != null ? (currentMove.cp_eval_after / 100).toFixed(1) : "—"}
                    </div>
                  </div>
                  <div style={{ padding: 8, background: "var(--bg-primary)", borderRadius: 4 }}>
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: 2 }}>CP Loss</div>
                    <div className="mono" style={{
                      fontSize: "0.9rem",
                      fontWeight: 600,
                      color: currentMove.cp_loss > 100 ? "var(--blunder)"
                        : currentMove.cp_loss > 50 ? "var(--mistake)"
                        : currentMove.cp_loss > 20 ? "var(--inaccuracy)"
                        : "var(--text-primary)",
                    }}>
                      {currentMove.cp_loss != null ? `−${currentMove.cp_loss.toFixed(0)}` : "—"}
                    </div>
                  </div>
                </div>

                {/* Best move */}
                {currentMove.best_move_san && currentMove.mistake_severity && (
                  <div style={{ marginBottom: 12, padding: "8px 12px", background: "var(--bg-primary)", borderRadius: 4, borderLeft: "3px solid var(--accent)" }}>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Best move: </span>
                    <span className="mono" style={{ fontWeight: 600 }}>{currentMove.best_move_san}</span>
                  </div>
                )}

                {/* Pattern annotation */}
                {currentMistake?.pattern_matches?.length > 0 && (
                  <div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 6, fontWeight: 600 }}>
                      Pattern Analysis
                    </div>
                    {currentMistake.pattern_matches.map((pm, i) => (
                      <div
                        key={i}
                        style={{
                          padding: "8px 12px",
                          background: "var(--bg-primary)",
                          borderRadius: 4,
                          marginBottom: 4,
                          borderLeft: "3px solid var(--mistake)",
                        }}
                      >
                        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 2 }}>
                          {pm.registry_pattern_id}
                        </div>
                        <div style={{ fontSize: "0.85rem", lineHeight: 1.5 }}>
                          {pm.annotation}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* No annotation yet */}
                {currentMove.mistake_severity && (!currentMistake || currentMistake.pattern_matches?.length === 0) && (
                  <div style={{ padding: "8px 12px", background: "var(--bg-primary)", borderRadius: 4, color: "var(--text-muted)", fontSize: "0.85rem" }}>
                    {game.annotation_status === "complete"
                      ? "No pattern match for this mistake"
                      : "Annotation pending — pattern details will appear after AI analysis"}
                  </div>
                )}

                {/* No mistake on this move */}
                {!currentMove.mistake_severity && (
                  <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                    Good move — no issues detected
                  </div>
                )}
              </div>
            ) : (
              <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                Select a move to see details. Use arrow keys or click in the move list.
              </div>
            )}
          </div>
        </div>
      )}

      {gameLoading && (
        <p style={{ marginTop: 20, color: "var(--text-muted)" }}>Loading game...</p>
      )}

      {!game && !gameLoading && (
        <p style={{ marginTop: 20, color: "var(--text-muted)" }}>
          Select a game from the list to begin analysis review.
        </p>
      )}
    </div>
  );
}
