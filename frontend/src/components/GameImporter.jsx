import { useCallback, useState } from "react";
import { importChessCom, importLichess, uploadPGN } from "../api/client";

/**
 * Game import panel for Lichess, Chess.com, and PGN upload.
 */
export default function GameImporter({ onImportComplete }) {
  const [tab, setTab] = useState("lichess");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  // Lichess state
  const [lichessUser, setLichessUser] = useState("");
  const [lichessSince, setLichessSince] = useState("");
  const [lichessColor, setLichessColor] = useState("both");
  const [lichessRated, setLichessRated] = useState("both");
  const [lichessTimeControl, setLichessTimeControl] = useState("all");

  // Chess.com state
  const [chesscomUser, setChesscomUser] = useState("");
  const [chesscomYear, setChesscomYear] = useState("");
  const [chesscomMonth, setChesscomMonth] = useState("");

  // PGN paste state
  const [pgnText, setPgnText] = useState("");

  const handleLichessImport = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      const result = await importLichess(lichessUser, {
        since: lichessSince || null,
        color: lichessColor !== "both" ? lichessColor : null,
        rated: lichessRated !== "both" ? lichessRated === "rated" : null,
        time_control: lichessTimeControl !== "all" ? lichessTimeControl : null,
      });
      setMessage({
        type: "success",
        text: `Imported ${result.imported ?? 0} game(s) for ${lichessUser}. ${result.skipped ?? 0} duplicate(s) skipped.`,
      });
      onImportComplete?.(result);
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  }, [lichessUser, lichessSince, lichessColor, lichessRated, lichessTimeControl, onImportComplete]);

  const handleChesscomImport = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      const result = await importChessCom(
        chesscomUser,
        chesscomYear || null,
        chesscomMonth || null
      );
      setMessage({
        type: "success",
        text: `Imported ${result.imported ?? 0} game(s) for ${chesscomUser}. ${result.skipped ?? 0} duplicate(s) skipped.`,
      });
      onImportComplete?.(result);
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  }, [chesscomUser, chesscomYear, chesscomMonth, onImportComplete]);

  const handleFileUpload = useCallback(
    async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      setLoading(true);
      setMessage(null);
      try {
        const result = await uploadPGN(file);
        setMessage({
          type: "success",
          text: `Imported ${result.imported ?? 0} game(s) from PGN file.`,
        });
        onImportComplete?.(result);
      } catch (err) {
        setMessage({ type: "error", text: err.message });
      } finally {
        setLoading(false);
      }
    },
    [onImportComplete]
  );

  const handlePgnPaste = useCallback(async () => {
    if (!pgnText.trim()) return;
    setLoading(true);
    setMessage(null);
    try {
      const blob = new Blob([pgnText], { type: "application/x-chess-pgn" });
      const file = new File([blob], "pasted.pgn", { type: "application/x-chess-pgn" });
      const result = await uploadPGN(file);
      setMessage({
        type: "success",
        text: `Imported ${result.imported ?? 0} game(s) from pasted PGN.`,
      });
      setPgnText("");
      onImportComplete?.(result);
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  }, [pgnText, onImportComplete]);

  return (
    <div className="card">
      <div style={{ display: "flex", gap: 4, marginBottom: 16 }}>
        {["lichess", "chesscom", "pgn"].map((t) => (
          <button
            key={t}
            className={`btn ${tab === t ? "btn-primary" : "btn-secondary"}`}
            onClick={() => { setTab(t); setMessage(null); }}
          >
            {t === "lichess" ? "Lichess" : t === "chesscom" ? "Chess.com" : "PGN Upload"}
          </button>
        ))}
      </div>

      {tab === "lichess" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <label style={labelStyle}>
            Username
            <input
              placeholder="e.g. DrNykterstein"
              value={lichessUser}
              onChange={(e) => setLichessUser(e.target.value)}
              style={inputStyle}
            />
          </label>
          <label style={labelStyle}>
            Since date (optional — leave blank to import all games)
            <input
              type="date"
              value={lichessSince}
              onChange={(e) => setLichessSince(e.target.value)}
              style={inputStyle}
            />
          </label>
          <div style={{ display: "flex", gap: 8 }}>
            <label style={{ ...labelStyle, flex: 1 }}>
              Color
              <select
                value={lichessColor}
                onChange={(e) => setLichessColor(e.target.value)}
                style={inputStyle}
              >
                <option value="both">Both</option>
                <option value="white">White</option>
                <option value="black">Black</option>
              </select>
            </label>
            <label style={{ ...labelStyle, flex: 1 }}>
              Rated
              <select
                value={lichessRated}
                onChange={(e) => setLichessRated(e.target.value)}
                style={inputStyle}
              >
                <option value="both">Both</option>
                <option value="rated">Rated only</option>
                <option value="casual">Casual only</option>
              </select>
            </label>
            <label style={{ ...labelStyle, flex: 1 }}>
              Time control
              <select
                value={lichessTimeControl}
                onChange={(e) => setLichessTimeControl(e.target.value)}
                style={inputStyle}
              >
                <option value="all">All</option>
                <option value="bullet">Bullet</option>
                <option value="blitz">Blitz</option>
                <option value="rapid">Rapid</option>
                <option value="classical">Classical</option>
                <option value="correspondence">Correspondence</option>
              </select>
            </label>
          </div>
          <button className="btn btn-primary" onClick={handleLichessImport} disabled={loading || !lichessUser}>
            {loading ? "Importing..." : "Import All Games from Lichess"}
          </button>
          <p style={{ fontSize: "0.7rem", color: "var(--text-secondary)", margin: 0 }}>
            Imports all games by default. Use the filters above to narrow down. Duplicates are automatically skipped.
          </p>
        </div>
      )}

      {tab === "chesscom" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <label style={labelStyle}>
            Username
            <input
              placeholder="e.g. MagnusCarlsen"
              value={chesscomUser}
              onChange={(e) => setChesscomUser(e.target.value)}
              style={inputStyle}
            />
          </label>
          <div style={{ display: "flex", gap: 8 }}>
            <label style={{ ...labelStyle, flex: 1 }}>
              Year
              <input
                type="number"
                placeholder="e.g. 2025"
                min={2007}
                value={chesscomYear}
                onChange={(e) => setChesscomYear(e.target.value)}
                style={inputStyle}
              />
            </label>
            <label style={{ ...labelStyle, flex: 1 }}>
              Month
              <input
                type="number"
                placeholder="1-12"
                min={1}
                max={12}
                value={chesscomMonth}
                onChange={(e) => setChesscomMonth(e.target.value)}
                style={inputStyle}
              />
            </label>
          </div>
          <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
            Leave year/month blank to import the most recent month.
          </p>
          <button className="btn btn-primary" onClick={handleChesscomImport} disabled={loading || !chesscomUser}>
            {loading ? "Importing..." : "Import from Chess.com"}
          </button>
        </div>
      )}

      {tab === "pgn" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <label
            style={{
              ...inputStyle,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              minHeight: 60,
              borderStyle: "dashed",
            }}
          >
            {loading ? "Uploading..." : "Click to select a .pgn file"}
            <input type="file" accept=".pgn" onChange={handleFileUpload} style={{ display: "none" }} />
          </label>
          <div style={{ textAlign: "center", fontSize: "0.8rem", color: "var(--text-secondary)" }}>or paste PGN below</div>
          <textarea
            placeholder={"[Event \"...\"]\n[White \"...\"]\n...\n\n1. e4 e5 2. Nf3 ..."}
            value={pgnText}
            onChange={(e) => setPgnText(e.target.value)}
            rows={8}
            style={{ ...inputStyle, fontFamily: "monospace", resize: "vertical" }}
          />
          <button className="btn btn-primary" onClick={handlePgnPaste} disabled={loading || !pgnText.trim()}>
            {loading ? "Importing..." : "Import Pasted PGN"}
          </button>
        </div>
      )}

      {message && (
        <div
          style={{
            marginTop: 12,
            padding: "0.5rem 0.75rem",
            borderRadius: 4,
            fontSize: "0.85rem",
            backgroundColor: message.type === "error" ? "rgba(244,67,54,0.1)" : "rgba(76,175,80,0.1)",
            color: message.type === "error" ? "var(--error)" : "var(--success)",
          }}
        >
          {message.text}
        </div>
      )}
    </div>
  );
}

const labelStyle = {
  display: "flex",
  flexDirection: "column",
  gap: 4,
  fontSize: "0.8rem",
  color: "var(--text-secondary)",
};

const inputStyle = {
  padding: "0.5rem 0.75rem",
  borderRadius: 6,
  border: "1px solid var(--border)",
  backgroundColor: "var(--bg-secondary)",
  color: "var(--text-primary)",
  fontSize: "0.875rem",
};
