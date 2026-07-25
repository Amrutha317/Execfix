"use client";

import { useState } from "react";

import { runEval } from "@/lib/api";
import type { EvalResponse } from "@/lib/types";

export default function EvalPage() {
  const [model, setModel] = useState("gpt-5-mini");
  const [maxAttempts, setMaxAttempts] = useState(3);
  const [timeout, setTimeoutSeconds] = useState(30);
  const [limit, setLimit] = useState(5);
  const [only, setOnly] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<EvalResponse | null>(null);

  async function onRunEval() {
    setLoading(true);
    setError(null);
    try {
      const response = await runEval({
        model: model.trim() || undefined,
        max_attempts: maxAttempts,
        timeout,
        limit: Number.isFinite(limit) ? limit : undefined,
        only: only
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="row" style={{ alignItems: "flex-start" }}>
      <section className="card" style={{ width: 360 }}>
        <h3 style={{ marginTop: 0 }}>Run QuixBugs Eval</h3>
        <label>Model</label>
        <input value={model} onChange={(e) => setModel(e.target.value)} />
        <div style={{ height: 8 }} />
        <label>Max attempts</label>
        <input
          type="number"
          min={1}
          max={10}
          value={maxAttempts}
          onChange={(e) => setMaxAttempts(Number(e.target.value))}
        />
        <div style={{ height: 8 }} />
        <label>Timeout (s)</label>
        <input
          type="number"
          min={1}
          max={180}
          value={timeout}
          onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
        />
        <div style={{ height: 8 }} />
        <label>Limit (quick smoke)</label>
        <input
          type="number"
          min={1}
          max={100}
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
        />
        <div style={{ height: 8 }} />
        <label>Only (comma-separated problem names)</label>
        <input
          value={only}
          onChange={(e) => setOnly(e.target.value)}
          placeholder="gcd,bucketsort,lis"
        />
        <div style={{ height: 12 }} />
        <button onClick={onRunEval} disabled={loading}>
          {loading ? "Running..." : "Run Eval"}
        </button>
        {error ? <p className="error">{error}</p> : null}
      </section>

      <section className="card" style={{ flex: 1, minWidth: 400 }}>
        <h3 style={{ marginTop: 0 }}>Results</h3>
        {!result ? (
          <p className="muted">No eval run yet.</p>
        ) : (
          <>
            <p>
              Model: <strong>{result.model}</strong>
            </p>
            <p>
              Pass rate:{" "}
              <strong>
                {result.summary.passed}/{result.summary.evaluated} ({(result.summary.pass_rate * 100).toFixed(1)}%)
              </strong>
            </p>
            <p className="muted">
              Skipped: {result.summary.skipped}, Avg attempts when passed:{" "}
              {result.summary.avg_attempts_when_passed.toFixed(2)}
            </p>

            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th align="left">Problem</th>
                    <th align="left">Result</th>
                    <th align="left">Attempts</th>
                    <th align="left">Exception</th>
                  </tr>
                </thead>
                <tbody>
                  {result.results.map((r) => (
                    <tr key={r.name}>
                      <td>{r.name}</td>
                      <td>
                        {r.skipped_reason
                          ? `SKIP (${r.skipped_reason})`
                          : r.passed
                            ? "PASS"
                            : "FAIL"}
                      </td>
                      <td>{r.attempts_used}</td>
                      <td>{r.final_exception_type ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </main>
  );
}

