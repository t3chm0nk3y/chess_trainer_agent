import { useCallback, useEffect, useRef, useState } from "react";
import { getAnalysisStatus } from "../api/client";

/**
 * Hook for polling analysis job status.
 */
export default function useAnalysis(jobId) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  const poll = useCallback(async () => {
    if (!jobId) return;
    try {
      const result = await getAnalysisStatus(jobId);
      setStatus(result);
      if (result.status === "completed" || result.status === "failed") {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    } catch (err) {
      setError(err.message);
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;
    setStatus(null);
    setError(null);
    poll();
    intervalRef.current = setInterval(poll, 2000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [jobId, poll]);

  return { status, error, isLoading: status?.status === "running" };
}
