import { useEffect, useState } from "react";
import { listPatterns, getPattern } from "../api/client";

function PhaseBadge({ phase }) {
  const colors = {
    opening: "#2196f3",
    middlegame: "#ff9800",
    endgame: "#9c27b0",
    all: "#607d8b",
  };
  return (
    <span className="badge" style={{ backgroundColor: colors[phase] || "#666" }}>
      {phase}
    </span>
  );
}

function AxisBadge({ axis }) {
  const colors = { tactical: "#e91e63", strategic: "#00bcd4" };
  return (
    <span className="badge" style={{ backgroundColor: colors[axis] || "#666" }}>
      {axis}
    </span>
  );
}


function PatternCard({ pattern, onExpand, expanded }) {
  return (
    <div className="card" style={{ marginBottom: 8, padding: "12px 16px" }}>
      <div
        onClick={onExpand}
        style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}
      >
        <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>{pattern.name}</span>
        <PhaseBadge phase={pattern.phase} />
        <AxisBadge axis={pattern.axis} />
        <span className="mono" style={{ color: "var(--accent)", fontSize: "0.85rem" }}>
          &times;{pattern.frequency}
        </span>
        <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
          across {pattern.games_affected} games
        </span>
        <span style={{ marginLeft: "auto", color: "var(--text-muted)", fontSize: "0.75rem" }}>
          {pattern.last_seen_at?.slice(0, 10)}
        </span>
      </div>
      {pattern.example_annotation && (
        <p style={{ margin: "6px 0 0 0", color: "var(--text-muted)", fontSize: "0.8rem" }}>
          {pattern.example_annotation.slice(0, 120)}
        </p>
      )}
      {expanded && pattern.occurrences && (
        <div style={{ marginTop: 8, paddingLeft: 12, borderLeft: "2px solid var(--border)" }}>
          {pattern.occurrences.map((o, i) => (
            <div key={i} style={{ fontSize: "0.8rem", color: "var(--text-muted)", padding: "2px 0" }}>
              Game #{o.game_id} · {o.annotation?.slice(0, 80)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


const FILTER_TABS = [
  { key: "all", label: "All" },
  { key: "tactical", label: "Tactical" },
  { key: "strategic", label: "Strategic" },
  { key: "opening", label: "Opening" },
  { key: "middlegame", label: "Middlegame" },
  { key: "endgame", label: "Endgame" },
];

export default function PatternsPage() {
  const [patterns, setPatterns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    listPatterns({ limit: 500 })
      .then((p) => setPatterns(p.patterns || []))
      .finally(() => setLoading(false));
  }, []);

  const handleExpand = async (pattern) => {
    if (expandedId === pattern.id) {
      setExpandedId(null);
      return;
    }
    // Fetch full pattern with occurrences
    try {
      const full = await getPattern(pattern.id);
      setPatterns((prev) =>
        prev.map((p) => (p.id === pattern.id ? { ...p, occurrences: full.occurrences } : p))
      );
      setExpandedId(pattern.id);
    } catch {
      setExpandedId(pattern.id);
    }
  };

  // Filter mistake patterns (not game_condition)
  const mistakePatterns = patterns.filter((p) => p.axis !== "game_condition");
  const filtered = mistakePatterns.filter((p) => {
    if (filter === "all") return true;
    if (filter === "tactical" || filter === "strategic") return p.axis === filter;
    return p.phase === filter;
  });

  if (loading) return <p style={{ color: "var(--text-muted)" }}>Loading...</p>;

  return (
    <div>
      {/* Section A: Recurring Mistakes */}
      <h2 style={{ marginBottom: 12 }}>Recurring Mistakes</h2>
      <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            style={{
              backgroundColor: filter === tab.key ? "var(--accent)" : "var(--bg-elevated)",
              color: filter === tab.key ? "#fff" : "var(--text-primary)",
              border: "none",
              padding: "4px 12px",
              borderRadius: 4,
              cursor: "pointer",
              fontSize: "0.8rem",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p style={{ color: "var(--text-muted)" }}>No patterns found</p>
      ) : (
        filtered.map((p) => (
          <PatternCard
            key={p.id}
            pattern={p}
            expanded={expandedId === p.id}
            onExpand={() => handleExpand(p)}
          />
        ))
      )}

    </div>
  );
}
