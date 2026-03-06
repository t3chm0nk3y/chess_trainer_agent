import { useState } from "react";
import AnalysisSummary from "../components/AnalysisSummary";
import GameImporter from "../components/GameImporter";
import WorkflowProgress from "../components/WorkflowProgress";
import useAnalysis from "../hooks/useAnalysis";

export default function SubmitTab() {
  const [jobId, setJobId] = useState(null);
  const [importResult, setImportResult] = useState(null);
  const { status, error, isLoading } = useAnalysis(jobId);

  const handleImportComplete = (result) => {
    setImportResult(result);
    if (result?.job_id) {
      setJobId(result.job_id);
    }
  };

  return (
    <div style={{ maxWidth: 640 }}>
      <h2 style={{ fontSize: "1.1rem", marginBottom: 16 }}>Import Games</h2>
      <GameImporter onImportComplete={handleImportComplete} />

      {isLoading && status && (
        <WorkflowProgress run={status} />
      )}

      {error && (
        <div
          className="card"
          style={{
            marginTop: 12,
            color: "var(--error)",
            borderColor: "var(--error)",
          }}
        >
          Error: {error}
        </div>
      )}

      {status?.status === "completed" && (
        <AnalysisSummary
          game={importResult}
          moves={[]}
          matchedPatterns={[]}
        />
      )}
    </div>
  );
}
