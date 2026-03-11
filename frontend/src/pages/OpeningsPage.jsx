import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listOpenings, computeOpenings } from "../api/client";

function WLDBadges({ wins, losses, draws }) {
  return (
    <span style={{ display: "inline-flex", gap: 4 }}>
      <span className="badge" style={{ backgroundColor: "#4caf50" }}>
        {wins}W
      </span>
      <span className="badge" style={{ backgroundColor: "#f44336" }}>
        {losses}L
      </span>
      <span className="badge" style={{ backgroundColor: "#9e9e9e" }}>
        {draws}D
      </span>
    </span>
  );
}

export default function OpeningsPage() {
  const [openings, setOpenings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [computing, setComputing] = useState(false);
  const [minGames, setMinGames] = useState(3);
  const navigate = useNavigate();

  const load = () => {
    setLoading(true);
    listOpenings()
      .then((data) => setOpenings(data.openings || []))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleCompute = async () => {
    setComputing(true);
    try {
      await computeOpenings();
      load();
    } finally {
      setComputing(false);
    }
  };

  const filtered = openings.filter((o) => o.total_games >= minGames);

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h2 style={{ margin: 0 }}>Openings</h2>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <label style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
            Min games:{" "}
            <input
              type="number"
              value={minGames}
              onChange={(e) => setMinGames(Number(e.target.value))}
              min={1}
              style={{ width: 50 }}
            />
          </label>
          <button onClick={handleCompute} disabled={computing}>
            {computing ? "Computing..." : "Recompute"}
          </button>
        </div>
      </div>

      {loading ? (
        <p style={{ color: "var(--text-muted)" }}>Loading...</p>
      ) : filtered.length === 0 ? (
        <p style={{ color: "var(--text-muted)" }}>
          No opening stats yet. Click Recompute after engine analysis completes.
        </p>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th>ECO</th>
                <th>Opening</th>
                <th>Games</th>
                <th>W/L/D</th>
                <th style={{ textAlign: "right" }}>Loss %</th>
                <th style={{ textAlign: "right" }}>Avg CP Loss</th>
                <th>Divergence</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((o) => (
                <tr key={o.id} style={{ cursor: "pointer" }}>
                  <td className="mono" style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                    {o.eco_code}
                  </td>
                  <td>
                    <span style={{ fontWeight: 600 }}>{o.opening_name}</span>
                    {o.variation_name && (
                      <span
                        style={{
                          color: "var(--text-muted)",
                          fontStyle: "italic",
                          marginLeft: 6,
                        }}
                      >
                        {o.variation_name}
                      </span>
                    )}
                  </td>
                  <td className="mono" style={{ fontSize: "0.85rem" }}>
                    {o.total_games}
                  </td>
                  <td>
                    <WLDBadges wins={o.wins} losses={o.losses} draws={o.draws} />
                  </td>
                  <td
                    className="mono"
                    style={{
                      textAlign: "right",
                      color: o.loss_rate > 0.5 ? "#f44336" : "var(--text-primary)",
                      fontWeight: o.loss_rate > 0.5 ? 600 : 400,
                    }}
                  >
                    {(o.loss_rate * 100).toFixed(0)}%
                  </td>
                  <td className="mono" style={{ textAlign: "right", fontSize: "0.85rem" }}>
                    {o.avg_cp_loss_opening != null
                      ? o.avg_cp_loss_opening.toFixed(1)
                      : "—"}
                  </td>
                  <td style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    {o.divergence_move ? (
                      <>
                        Goes wrong at move {o.divergence_move}
                        {o.divergence_san && (
                          <span className="mono" style={{ marginLeft: 4 }}>
                            · {o.divergence_san}
                          </span>
                        )}
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
