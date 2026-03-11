import { useEffect, useState } from "react";
import { getConditions } from "../api/client";

function WLDBar({ wins, losses, draws, total }) {
  if (!total) return null;
  const wp = (wins / total) * 100;
  const lp = (losses / total) * 100;
  const dp = (draws / total) * 100;
  return (
    <div
      style={{
        display: "flex",
        height: 6,
        borderRadius: 3,
        overflow: "hidden",
        width: 120,
      }}
    >
      <div style={{ width: `${wp}%`, backgroundColor: "#4caf50" }} />
      <div style={{ width: `${dp}%`, backgroundColor: "#9e9e9e" }} />
      <div style={{ width: `${lp}%`, backgroundColor: "#f44336" }} />
    </div>
  );
}

function ConditionCard({ condition }) {
  return (
    <div className="card" style={{ marginBottom: 8, padding: "12px 16px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>{condition.name}</span>
        <span className="mono" style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
          {condition.total_games} games
        </span>
        <span style={{ color: "#f44336", fontSize: "0.85rem" }}>
          {condition.losses} losses ({(condition.loss_rate * 100).toFixed(0)}%)
        </span>
        <WLDBar
          wins={condition.wins}
          losses={condition.losses}
          draws={condition.draws}
          total={condition.total_games}
        />
      </div>
    </div>
  );
}

export default function ConditionsPage() {
  const [conditions, setConditions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getConditions()
      .then((c) => setConditions(c.conditions || []))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p style={{ color: "var(--text-muted)" }}>Loading...</p>;

  return (
    <div>
      <h2 style={{ marginTop: 0, marginBottom: 16 }}>Game Conditions</h2>
      {conditions.length === 0 ? (
        <p style={{ color: "var(--text-muted)" }}>
          No game conditions detected yet. Conditions are identified after engine analysis completes.
        </p>
      ) : (
        conditions.map((c) => (
          <ConditionCard key={c.registry_pattern_id} condition={c} />
        ))
      )}
    </div>
  );
}
