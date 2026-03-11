import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listGames } from "../api/client";

function ResultBadge({ result }) {
  const colors = { win: "#4caf50", loss: "#f44336", draw: "#9e9e9e" };
  return (
    <span
      className="badge"
      style={{ backgroundColor: colors[result] || "#666" }}
    >
      {result}
    </span>
  );
}

function StatusDot({ status }) {
  const colors = {
    complete: "#4caf50",
    pending: "#ff9800",
    running: "#2196f3",
    failed: "#f44336",
    needs_manual_review: "#9c27b0",
  };
  const labels = {
    complete: "✓",
    pending: "—",
    running: "⟳",
    failed: "✗",
    needs_manual_review: "!",
  };
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 22,
        height: 22,
        borderRadius: "50%",
        backgroundColor: colors[status] || "#666",
        color: "#fff",
        fontSize: "0.7rem",
        fontWeight: 700,
      }}
      title={status}
    >
      {labels[status] || "?"}
    </span>
  );
}

const COLUMNS = [
  { key: "played_at", label: "Date" },
  { key: "opponent_username", label: "Opponent" },
  { key: "result", label: "Result" },
  { key: "opening_name", label: "Opening" },
  { key: "time_control", label: "Time" },
  { key: "engine_status", label: "Engine" },
  { key: "annotation_status", label: "Annotation" },
];

function SortHeader({ column, sortKey, sortDir, onSort }) {
  const active = sortKey === column.key;
  const arrow = active ? (sortDir === "asc" ? " ▲" : " ▼") : "";
  return (
    <th
      onClick={() => onSort(column.key)}
      style={{ cursor: "pointer", userSelect: "none" }}
    >
      {column.label}
      <span style={{ fontSize: "0.65rem", marginLeft: 2 }}>{arrow}</span>
    </th>
  );
}

function sortGames(games, key, dir) {
  return [...games].sort((a, b) => {
    let av = a[key] ?? "";
    let bv = b[key] ?? "";
    if (typeof av === "string") av = av.toLowerCase();
    if (typeof bv === "string") bv = bv.toLowerCase();
    if (av < bv) return dir === "asc" ? -1 : 1;
    if (av > bv) return dir === "asc" ? 1 : -1;
    return 0;
  });
}

export default function GamesPage() {
  const [games, setGames] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [sortKey, setSortKey] = useState("played_at");
  const [sortDir, setSortDir] = useState("desc");
  const navigate = useNavigate();
  const limit = 50;

  useEffect(() => {
    setLoading(true);
    listGames({ limit, offset: page * limit })
      .then((data) => {
        setGames(data.games);
        setTotal(data.total);
      })
      .finally(() => setLoading(false));
  }, [page]);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const sorted = sortGames(games, sortKey, sortDir);
  const totalPages = Math.ceil(total / limit);

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>
        Games{" "}
        <span style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
          ({total})
        </span>
      </h2>

      {loading ? (
        <p style={{ color: "var(--text-muted)" }}>Loading...</p>
      ) : (
        <>
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {COLUMNS.map((col) => (
                    <SortHeader
                      key={col.key}
                      column={col}
                      sortKey={sortKey}
                      sortDir={sortDir}
                      onSort={handleSort}
                    />
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map((g) => (
                  <tr
                    key={g.id}
                    onClick={() => navigate(`/games/${g.id}`)}
                    style={{ cursor: "pointer" }}
                  >
                    <td className="mono" style={{ fontSize: "0.8rem" }}>
                      {g.played_at?.slice(0, 10)}
                    </td>
                    <td>{g.opponent_username || "—"}</td>
                    <td>
                      <ResultBadge result={g.result} />
                    </td>
                    <td style={{ maxWidth: 250, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {g.opening_name || g.eco_code || "—"}
                      {g.variation_name && (
                        <span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
                          {" "}
                          · {g.variation_name}
                        </span>
                      )}
                    </td>
                    <td className="mono" style={{ fontSize: "0.8rem" }}>
                      {g.time_control || "—"}
                    </td>
                    <td style={{ textAlign: "center" }}>
                      <StatusDot status={g.engine_status} />
                    </td>
                    <td style={{ textAlign: "center" }}>
                      <StatusDot status={g.annotation_status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div style={{ marginTop: 12, display: "flex", gap: 8, justifyContent: "center" }}>
              <button disabled={page === 0} onClick={() => setPage(page - 1)}>
                Prev
              </button>
              <span className="mono" style={{ padding: "6px 0", color: "var(--text-muted)" }}>
                {page + 1} / {totalPages}
              </span>
              <button disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
