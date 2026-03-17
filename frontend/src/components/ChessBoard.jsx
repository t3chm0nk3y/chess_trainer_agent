import { useMemo } from "react";

const PIECE_MAP = {
  p: "bP", r: "bR", n: "bN", b: "bB", q: "bQ", k: "bK",
  P: "wP", R: "wR", N: "wN", B: "wB", Q: "wQ", K: "wK",
};

const PIECE_UNICODE = {
  wK: "\u2654", wQ: "\u2655", wR: "\u2656", wB: "\u2657", wN: "\u2658", wP: "\u2659",
  bK: "\u265A", bQ: "\u265B", bR: "\u265C", bB: "\u265D", bN: "\u265E", bP: "\u265F",
};

const COLUMNS = "abcdefgh";

const LIGHT = "#edeed1";
const DARK = "#779952";

function fenToPosition(fen) {
  if (!fen) return {};
  const rows = fen.split(" ")[0].split("/");
  const position = {};
  for (let i = 0; i < 8; i++) {
    let col = 0;
    for (const ch of rows[i]) {
      if (ch >= "1" && ch <= "8") {
        col += parseInt(ch);
      } else {
        position[COLUMNS[col] + (8 - i)] = PIECE_MAP[ch];
        col++;
      }
    }
  }
  return position;
}

/**
 * Pure SVG chess board — no external dependencies.
 * Read-only display with FEN-based positioning.
 */
export default function ChessBoard({ fen, boardWidth = 320, orientation = "white" }) {
  const position = useMemo(() => fenToPosition(fen), [fen]);
  const flipped = orientation === "black";
  const sqSize = boardWidth / 8;
  const fontSize = sqSize * 0.85;

  return (
    <svg
      width={boardWidth}
      height={boardWidth}
      viewBox={`0 0 ${boardWidth} ${boardWidth}`}
      style={{ display: "block", userSelect: "none" }}
    >
      {Array.from({ length: 64 }, (_, idx) => {
        const fileIdx = idx % 8;
        const rankIdx = Math.floor(idx / 8);
        const displayFile = flipped ? 7 - fileIdx : fileIdx;
        const displayRank = flipped ? rankIdx : 7 - rankIdx;
        const square = COLUMNS[displayFile] + (displayRank + 1);
        const isLight = (displayFile + displayRank) % 2 === 1;
        const x = fileIdx * sqSize;
        const y = rankIdx * sqSize;
        const piece = position[square];

        return (
          <g key={square}>
            <rect
              x={x}
              y={y}
              width={sqSize}
              height={sqSize}
              fill={isLight ? LIGHT : DARK}
            />
            {piece && (
              <text
                x={x + sqSize / 2}
                y={y + sqSize / 2}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={fontSize}
                style={{ pointerEvents: "none" }}
              >
                {PIECE_UNICODE[piece]}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
