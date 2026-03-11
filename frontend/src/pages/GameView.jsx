import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getGame, getGameMistakes, getGameRecurring } from "../api/client";
import ChessBoard from "../components/ChessBoard";
import EvalBar from "../components/EvalBar";
import MoveList from "../components/MoveList";

function EvalDisplay({ eval: cp }) {
  const clamped = Math.max(-1000, Math.min(1000, cp));
  const pawns = (clamped / 100).toFixed(1);
  const isPositive = clamped >= 0;
  return (
    <span
      className="mono"
      style={{
        fontWeight: 700,
        fontSize: "0.9rem",
        color: isPositive ? "#e0e0e0" : "#909296",
        minWidth: 48,
      }}
    >
      {isPositive ? "+" : ""}{pawns}
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

function ResultBadge({ result }) {
  const colors = { win: "#4caf50", loss: "#f44336", draw: "#9e9e9e" };
  return (
    <span className="badge" style={{ backgroundColor: colors[result] || "#666" }}>
      {result}
    </span>
  );
}

export default function GameView() {
  const { id } = useParams();
  const [game, setGame] = useState(null);
  const [mistakes, setMistakes] = useState([]);
  const [recurring, setRecurring] = useState([]);
  const [currentPly, setCurrentPly] = useState(0);
  const [loading, setLoading] = useState(true);
  const [username, setUsername] = useState("");

  useEffect(() => {
    fetch("/api/config").then(r => r.json()).then(c => setUsername(c.username)).catch(() => {});
    Promise.all([getGame(id), getGameMistakes(id), getGameRecurring(id)])
      .then(([g, m, r]) => {
        setGame(g);
        setMistakes(m.mistakes || []);
        setRecurring(r.recurring || []);
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <p style={{ color: "var(--text-muted)" }}>Loading...</p>;
  if (!game) return <p>Game not found</p>;

  // Prepare moves with ply index
  const moves = (game.moves || []).map((m, i) => ({ ...m, ply: i }));

  // Current position FEN
  const currentFen =
    currentPly > 0 && moves[currentPly - 1]
      ? moves[currentPly - 1].fen_after
      : "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

  // Current move info
  const currentMove = currentPly > 0 ? moves[currentPly - 1] : null;

  // Navigate to a mistake move
  const goToMistake = (moveNumber, color) => {
    const idx = moves.findIndex(
      (m) => m.move_number === moveNumber && m.color === color
    );
    if (idx >= 0) setCurrentPly(idx);
  };

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <Link to="/games" style={{ color: "var(--accent)", textDecoration: "none" }}>
          &larr; Games
        </Link>
      </div>

      {/* Header */}
      <div style={{ marginBottom: 16, display: "flex", gap: 12, alignItems: "center" }}>
        <ResultBadge result={game.result} />
        <span style={{ fontWeight: 600 }}>
          {game.opening_name || game.eco_code || "Unknown Opening"}
        </span>
        {game.variation_name && (
          <span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
            {game.variation_name}
          </span>
        )}
        <span style={{ color: "var(--text-muted)" }}>
          vs {game.opponent_username || "Unknown"}
        </span>
        <span className="mono" style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
          {game.played_at?.slice(0, 10)}
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "396px 1fr", gap: 24 }}>
        {/* Left column: EvalBar + Board + Move List */}
        <div style={{ width: 396 }}>
          {/* Opponent name (top of board) */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, paddingLeft: 36 }}>
            <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>
              {game.opponent_username || "Unknown"}
            </span>
            <span className="badge" style={{ backgroundColor: game.player_color === "white" ? "#333" : "#f0f0f0", color: game.player_color === "white" ? "#f0f0f0" : "#333" }}>
              {game.player_color === "white" ? "black" : "white"}
            </span>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <EvalBar
              eval_cp={currentMove?.cp_eval_after ?? 0}
              height={360}
            />
            <ChessBoard
              fen={currentFen}
              boardWidth={360}
              orientation={game.player_color || "white"}
            />
          </div>
          {/* Player name (bottom of board) */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4, paddingLeft: 36 }}>
            <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--accent)" }}>
              {username || "You"}
            </span>
            <span className="badge" style={{ backgroundColor: game.player_color === "white" ? "#f0f0f0" : "#333", color: game.player_color === "white" ? "#333" : "#f0f0f0" }}>
              {game.player_color}
            </span>
          </div>
          {/* Eval bar for current move */}
          {currentMove && currentMove.cp_eval_after != null && (
            <div
              style={{
                marginTop: 8,
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "8px 12px",
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: 4,
              }}
            >
              <EvalDisplay eval={currentMove.cp_eval_after} />
              {currentMove.mistake_severity && (
                <SeverityBadge severity={currentMove.mistake_severity} />
              )}
              {currentMove.cp_loss > 0 && (
                <span className="mono" style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                  −{currentMove.cp_loss.toFixed(0)}cp
                </span>
              )}
              {currentMove.best_move_san && currentMove.mistake_severity && (
                <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                  Best: <span className="mono">{currentMove.best_move_san}</span>
                </span>
              )}
            </div>
          )}
          <div style={{ marginTop: 8 }}>
            <MoveList
              moves={moves}
              currentPly={currentPly}
              onSelectPly={setCurrentPly}
            />
          </div>
        </div>

        {/* Right column: Analysis */}
        <div style={{ minWidth: 0 }}>
          {/* Section A: This Game — Mistakes */}
          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ margin: "0 0 12px 0", fontSize: "0.95rem" }}>
              Mistakes
              <span style={{ color: "var(--text-muted)", fontWeight: 400, marginLeft: 8 }}>
                {mistakes.length}
              </span>
            </h3>
            {mistakes.length === 0 ? (
              <p style={{ color: "var(--text-muted)", margin: 0 }}>
                {game.engine_status === "complete"
                  ? "No mistakes found"
                  : "Engine analysis pending"}
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {mistakes.map((m) => (
                  <div
                    key={m.id}
                    onClick={() => goToMistake(m.move_number, m.color)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "4px 8px",
                      cursor: "pointer",
                      borderRadius: 4,
                    }}
                    className="hover-row"
                  >
                    <span className="mono" style={{ width: 32, fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      {m.move_number}.
                    </span>
                    <span className="mono" style={{ width: 48, fontSize: "0.85rem" }}>
                      {m.san}
                    </span>
                    <SeverityBadge severity={m.mistake_severity} />
                    <span
                      style={{
                        color: "var(--text-muted)",
                        fontSize: "0.8rem",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        flex: 1,
                      }}
                    >
                      {m.pattern_matches?.[0]?.annotation?.slice(0, 60) || `−${m.cp_loss?.toFixed(0)}cp`}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Section B: Recurring Patterns */}
          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ margin: "0 0 12px 0", fontSize: "0.95rem" }}>
              Recurring Patterns
            </h3>
            {recurring.length === 0 ? (
              <p style={{ color: "var(--text-muted)", margin: 0 }}>
                No recurring patterns in this game
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {recurring.map((r, i) => (
                  <div
                    key={i}
                    onClick={() => goToMistake(r.move_number, "white")}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "4px 8px",
                      cursor: "pointer",
                      borderRadius: 4,
                    }}
                    className="hover-row"
                  >
                    <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>
                      {r.pattern_name}
                    </span>
                    <span className="badge" style={{ backgroundColor: "var(--accent)" }}>
                      &times;{r.frequency}
                    </span>
                    <span
                      style={{
                        color: "var(--text-muted)",
                        fontSize: "0.8rem",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        flex: 1,
                      }}
                    >
                      {r.annotation?.slice(0, 60)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Game Conditions */}
          {game.conditions && game.conditions.length > 0 && (
            <div className="card">
              <h3 style={{ margin: "0 0 12px 0", fontSize: "0.95rem" }}>
                Game Conditions
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {game.conditions.map((c, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "4px 8px",
                      fontSize: "0.85rem",
                    }}
                  >
                    <span style={{ fontWeight: 600 }}>{c.condition_name}</span>
                    {c.detected_at_move && (
                      <span className="mono" style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                        move {c.detected_at_move}
                      </span>
                    )}
                    {c.context_note && (
                      <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                        — {c.context_note}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
