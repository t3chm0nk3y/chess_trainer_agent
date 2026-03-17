export default function HelpPage() {
  const sections = [
    {
      title: "What is Chess Trainer?",
      content:
        "Chess Trainer is a personal coaching app that analyzes your Lichess game history, identifies recurring mistakes, and tracks your improvement over time. It uses Stockfish engine analysis combined with AI-powered annotations to surface the patterns holding you back from your next rating milestone.",
    },
    {
      title: "Getting Started",
      steps: [
        "Go to Settings and enter your Lichess username and API token.",
        "Import your games — choose how many recent games to pull in (50, 100, 500, or all).",
        "The engine analysis pipeline will automatically process your imported games.",
        "Once analysis is complete, explore your results across the other tabs.",
      ],
    },
    {
      title: "Dashboard",
      content:
        "Your home screen. See total game counts, how many have been analyzed and annotated, pipeline progress bars for each processing stage (Engine, Annotation, Conditions), your 10 most recent games, and your top recurring mistake patterns. The dashboard auto-refreshes every 30 seconds.",
    },
    {
      title: "Analysis",
      content:
        "Deep-dive into individual games with an interactive chessboard. Step through moves with arrow keys or navigation buttons, see the evaluation bar update in real time, and review AI annotations that explain what went wrong at each critical moment. The move list highlights inaccuracies, mistakes, and blunders with color-coded severity.",
    },
    {
      title: "Games",
      content:
        "Browse your full game library with sortable columns: date, opponent, result, opening, time control, and pipeline status. Click any game to open it in the Analysis view. Status dots show whether engine analysis and AI annotation are complete, running, pending, or failed for each game.",
    },
    {
      title: "Openings",
      content:
        "See aggregated statistics for every opening you play. Openings are ranked by loss rate so you can quickly identify which lines are costing you the most points. Each opening shows win/loss/draw counts, average centipawn loss, and the typical move where you start to diverge from strong play.",
    },
    {
      title: "Patterns",
      content:
        "Your recurring mistake patterns organized by game phase (opening, middlegame, endgame) and type (tactical or strategic). Each pattern shows how many games it affects and its frequency. Patterns are detected automatically from engine analysis and AI annotations, giving you a clear picture of what to study.",
    },
    {
      title: "Conditions",
      content:
        "Game conditions are situational factors detected during your games — things like time pressure, material imbalances, or positional characteristics. This tab shows how you perform under each condition with win/loss/draw breakdowns, helping you understand which situations you handle well and which need work.",
    },
    {
      title: "Reports",
      content:
        "Pre-generated reports across seven categories: Player Profile, Opening Analysis, Pattern Breakdowns, Monthly Summaries, Game Phase Analysis, Condition Reports, and Weakness Reports. Each report provides dense, structured insights. Use the type filter to browse by category, and click any report to see full details.",
    },
    {
      title: "Settings",
      content:
        "Configure your Lichess account (username and API token), adjust Stockfish analysis depth (higher means more accurate but slower), import games from Lichess, and restart the application after configuration changes.",
    },
    {
      title: "Analysis Pipeline",
      content:
        "Games are processed through a three-stage pipeline. First, Stockfish engine analysis evaluates every move and assigns centipawn loss scores. Second, AI annotation reviews the engine data and writes human-readable explanations of mistakes. Third, condition detection identifies situational patterns like time pressure or material imbalances. You can track the progress of each stage on the Dashboard.",
    },
    {
      title: "Keyboard Shortcuts",
      shortcuts: [
        { keys: "Left Arrow", action: "Previous move (in Analysis view)" },
        { keys: "Right Arrow", action: "Next move (in Analysis view)" },
        { keys: "Home", action: "Go to starting position" },
        { keys: "End", action: "Go to last move" },
      ],
    },
    {
      title: "Tips",
      tips: [
        "Import at least 100 games for meaningful pattern detection.",
        "Higher Stockfish depth (20+) gives better analysis but takes longer per game.",
        "Check the Dashboard regularly to monitor pipeline progress.",
        "Focus on patterns with the highest frequency first — those are your most impactful areas for improvement.",
        "Use the Reports tab for a comprehensive overview before diving into individual games.",
      ],
    },
  ];

  return (
    <div style={{ maxWidth: 800 }}>
      <h2 style={{ marginTop: 0, marginBottom: 20 }}>Help</h2>

      {sections.map((section) => (
        <div key={section.title} className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ margin: "0 0 10px 0", fontSize: "0.95rem" }}>{section.title}</h3>

          {section.content && (
            <p style={{ margin: 0, fontSize: "0.85rem", lineHeight: 1.6, color: "var(--text-secondary)" }}>
              {section.content}
            </p>
          )}

          {section.steps && (
            <ol style={{ margin: 0, paddingLeft: 20, fontSize: "0.85rem", lineHeight: 1.8, color: "var(--text-secondary)" }}>
              {section.steps.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
          )}

          {section.shortcuts && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {section.shortcuts.map((s) => (
                <div key={s.keys} style={{ display: "flex", alignItems: "center", gap: 12, fontSize: "0.85rem" }}>
                  <kbd
                    style={{
                      padding: "2px 8px",
                      background: "var(--bg-elevated)",
                      border: "1px solid var(--border)",
                      borderRadius: 4,
                      fontFamily: "inherit",
                      fontSize: "0.8rem",
                      minWidth: 80,
                      textAlign: "center",
                    }}
                  >
                    {s.keys}
                  </kbd>
                  <span style={{ color: "var(--text-secondary)" }}>{s.action}</span>
                </div>
              ))}
            </div>
          )}

          {section.tips && (
            <ul style={{ margin: 0, paddingLeft: 20, fontSize: "0.85rem", lineHeight: 1.8, color: "var(--text-secondary)" }}>
              {section.tips.map((tip, i) => (
                <li key={i}>{tip}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}
