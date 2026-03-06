import { useCallback, useEffect, useState } from "react";
import ChessBoard from "../components/ChessBoard";
import EvalBar from "../components/EvalBar";
import EvalGraph from "../components/EvalGraph";
import MoveList from "../components/MoveList";
import ThemeBadges from "../components/ThemeBadges";
import useChessGame from "../hooks/useChessGame";
import { getGame, getGameMoves, listGames } from "../api/client";

const BOARD_SIZES = [240, 280, 320, 360, 400, 440, 480, 520];
const DEFAULT_BOARD_SIZE = 320;

export default function AnalysisTab() {
  const [games, setGames] = useState([]);
  const [selectedGameId, setSelectedGameId] = useState(null);
  const [moves, setMoves] = useState([]);
  const [game, setGame] = useState(null);
  const [boardSize, setBoardSize] = useState(() => {
    const saved = localStorage.getItem("chess-board-size");
    return saved ? Number(saved) : DEFAULT_BOARD_SIZE;
  });

  const {
    currentPly,
    currentFen,
    currentMove,
    goForward,
    goBack,
    goToStart,
    goToEnd,
    goToPly,
  } = useChessGame(moves);

  useEffect(() => {
    listGames({ limit: 2000 }).then((res) => setGames(res.games || []));
  }, []);

  const selectGame = useCallback(async (id) => {
    setSelectedGameId(id);
    const [gameData, movesData] = await Promise.all([
      getGame(id),
      getGameMoves(id),
    ]);
    setGame(gameData);
    setMoves(movesData.moves || []);
  }, []);

  const handleBoardSizeChange = useCallback((e) => {
    const size = Number(e.target.value);
    setBoardSize(size);
    localStorage.setItem("chess-board-size", size);
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handler = (e) => {
      if (e.key === "ArrowRight") goForward();
      else if (e.key === "ArrowLeft") goBack();
      else if (e.key === "Home") goToStart();
      else if (e.key === "End") goToEnd();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [goForward, goBack, goToStart, goToEnd]);

  return (
    <div style={{ display: "flex", gap: 24 }}>
      {/* Left: Board + eval bar */}
      <div style={{ flexShrink: 0 }}>
        {/* Top player name (opponent from our perspective) */}
        {game && (
          <div style={{ display: "flex", gap: 8 }}>
            <div style={{ width: 28 }} />
            <PlayerLabel
              name={game.player_color === "white" ? game.black : game.white}
              color={game.player_color === "white" ? "black" : "white"}
            />
          </div>
        )}
        <div style={{ display: "flex", gap: 8 }}>
          <EvalBar
            eval_cp={currentMove?.engine_eval_after || 0}
            height={boardSize}
          />
          <ChessBoard
            fen={currentFen}
            boardWidth={boardSize}
            orientation={game?.player_color || "white"}
          />
        </div>
        {/* Bottom player name (us) */}
        {game && (
          <div style={{ display: "flex", gap: 8 }}>
            <div style={{ width: 28 }} />
            <PlayerLabel
              name={game.player_color === "white" ? game.white : game.black}
              color={game.player_color}
              isPlayer
            />
          </div>
        )}
        <EvalGraph
          moves={moves}
          currentPly={currentPly}
          onClickPly={goToPly}
        />
        {/* Navigation buttons */}
        <div style={{ display: "flex", gap: 8, marginTop: 8, justifyContent: "center" }}>
          <button className="btn btn-secondary" onClick={goToStart}>&laquo;</button>
          <button className="btn btn-secondary" onClick={goBack}>&lsaquo;</button>
          <button className="btn btn-secondary" onClick={goForward}>&rsaquo;</button>
          <button className="btn btn-secondary" onClick={goToEnd}>&raquo;</button>
        </div>
        {/* Board size slider */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, justifyContent: "center" }}>
          <span style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>Board size</span>
          <input
            type="range"
            min={BOARD_SIZES[0]}
            max={BOARD_SIZES[BOARD_SIZES.length - 1]}
            step={20}
            value={boardSize}
            onChange={handleBoardSizeChange}
            style={{ width: 120, accentColor: "var(--accent)" }}
          />
          <span className="mono" style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>
            {boardSize}px
          </span>
        </div>
      </div>

      {/* Right: Game selector + move list + annotation */}
      <div style={{ flex: 1, minWidth: 260 }}>
        <select
          value={selectedGameId || ""}
          onChange={(e) => e.target.value && selectGame(e.target.value)}
          style={{
            width: "100%",
            padding: "0.5rem",
            marginBottom: 12,
            backgroundColor: "var(--bg-card)",
            color: "var(--text-primary)",
            border: "1px solid var(--border)",
            borderRadius: 6,
          }}
        >
          <option value="">Select a game ({games.length} available)...</option>
          {games.map((g) => (
            <option key={g.id} value={g.id}>
              {g.white} vs {g.black} ({g.date_played || "?"}) {g.result}
            </option>
          ))}
        </select>

        <MoveList
          moves={moves}
          currentPly={currentPly}
          onSelectPly={goToPly}
        />

        {/* Current move annotation */}
        {currentMove && (
          <div className="card" style={{ marginTop: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span className="mono" style={{ fontSize: "1.1rem" }}>
                {currentMove.move_number}. {currentMove.san}
              </span>
              {currentMove.classification && (
                <span className={`badge badge-${currentMove.classification}`}>
                  {currentMove.classification}
                </span>
              )}
            </div>
            {currentMove.eval_delta != null && (
              <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginBottom: 4 }}>
                Eval: {(currentMove.engine_eval_after / 100).toFixed(1)} (delta:{" "}
                {(currentMove.eval_delta / 100).toFixed(1)})
              </div>
            )}
            <ThemeBadges
              themes={currentMove.themes_json ? JSON.parse(currentMove.themes_json) : null}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function PlayerLabel({ name, color, isPlayer = false }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        padding: "3px 0",
        fontSize: "0.8rem",
      }}
    >
      <div
        style={{
          width: 10,
          height: 10,
          borderRadius: 2,
          backgroundColor: color === "white" ? "#f0f0f0" : "#333",
          border: "1px solid var(--border)",
          flexShrink: 0,
        }}
      />
      <span style={{ color: isPlayer ? "var(--accent)" : "var(--text-primary)", fontWeight: isPlayer ? 600 : 400 }}>
        {name}
      </span>
      {isPlayer && (
        <span style={{ fontSize: "0.65rem", color: "var(--text-secondary)" }}>(you)</span>
      )}
    </div>
  );
}
