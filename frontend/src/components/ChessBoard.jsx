import { Chessboard } from "react-chessboard";

/**
 * Interactive chess board with position display.
 */
export default function ChessBoard({ fen, boardWidth = 320, orientation = "white" }) {
  return (
    <Chessboard
      position={fen}
      boardWidth={boardWidth}
      boardOrientation={orientation}
      arePiecesDraggable={false}
      animationDuration={150}
      customBoardStyle={{
        borderRadius: "0px",
      }}
      customDarkSquareStyle={{ backgroundColor: "#779952" }}
      customLightSquareStyle={{ backgroundColor: "#edeed1" }}
    />
  );
}
