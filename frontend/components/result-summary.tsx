"use client";

import type { DebugResponse } from "@/lib/types";

export default function ResultSummary({ result }: { result: DebugResponse }) {
  return (
    <div className="resultCardCompact">
      <h3>
        {result.success ? (
          <span className="success">Fixed in {result.attempts_used} attempt(s)</span>
        ) : (
          <span className="error">Failed after {result.attempts_used} attempt(s)</span>
        )}
      </h3>
      {result.final_exception_type ? (
        <p className="muted" style={{ margin: "0 0 8px", fontSize: 13 }}>
          Final exception: {result.final_exception_type}
        </p>
      ) : null}
      {result.final_error ? (
        <>
          <p className="muted" style={{ margin: "0 0 6px", fontSize: 12 }}>
            Final error
          </p>
          <pre className="error" style={{ marginBottom: 12 }}>
            {result.final_error}
          </pre>
        </>
      ) : null}
      <p className="muted" style={{ margin: "0 0 6px", fontSize: 12 }}>
        Final code
      </p>
      <pre>{result.final_code}</pre>
    </div>
  );
}
