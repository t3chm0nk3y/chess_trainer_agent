/**
 * Display ChessAgine positional theme indicators.
 */
export default function ThemeBadges({ themes }) {
  if (!themes) return null;

  const themeConfig = {
    material: { label: "Material", icon: "M" },
    mobility: { label: "Mobility", icon: "B" },
    space: { label: "Space", icon: "S" },
    king_safety: { label: "King Safety", icon: "K" },
  };

  return (
    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
      {Object.entries(themes).map(([key, value]) => {
        const config = themeConfig[key];
        if (!config || value == null) return null;
        const color = value > 0.5 ? "var(--success)" : value < -0.5 ? "var(--error)" : "var(--text-secondary)";
        return (
          <span
            key={key}
            title={`${config.label}: ${value.toFixed(1)}`}
            style={{
              fontSize: "0.65rem",
              padding: "1px 4px",
              borderRadius: 3,
              border: `1px solid ${color}`,
              color,
            }}
          >
            {config.icon}
          </span>
        );
      })}
    </div>
  );
}
