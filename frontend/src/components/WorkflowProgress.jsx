/**
 * Workflow step tracker showing progress through analysis pipeline.
 */
export default function WorkflowProgress({ run }) {
  if (!run) return null;

  const steps = run.step_results || [];
  const isRunning = run.status === "running";
  const isFailed = run.status === "failed";

  return (
    <div className="card" style={{ marginTop: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <h4 style={{ fontSize: "0.85rem" }}>{run.workflow}</h4>
        <span
          className="badge"
          style={{
            backgroundColor: isFailed
              ? "var(--error)"
              : isRunning
                ? "var(--accent)"
                : "var(--success)",
            color: "#fff",
          }}
        >
          {run.status}
        </span>
      </div>
      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
        {steps.map((step, i) => (
          <div
            key={i}
            title={`Step ${step.step}`}
            style={{
              flex: 1,
              height: 4,
              borderRadius: 2,
              backgroundColor: "var(--success)",
            }}
          />
        ))}
        {isRunning && (
          <div
            style={{
              flex: 1,
              height: 4,
              borderRadius: 2,
              backgroundColor: "var(--accent)",
              animation: "pulse 1.5s infinite",
            }}
          />
        )}
      </div>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}
