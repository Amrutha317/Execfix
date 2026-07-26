"use client";

import { useEffect, useState } from "react";

import AttemptTimeline from "@/components/attempt-timeline";
import ResultSummary from "@/components/result-summary";
import { clearHistory, getHistory, type HistoryRun } from "@/lib/history";

function formatTimestamp(ms: number) {
  return new Date(ms).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function codePreview(code: string) {
  const firstLine = code.split("\n").find((l) => l.trim().length > 0) ?? "";
  return firstLine.length > 60 ? `${firstLine.slice(0, 60)}…` : firstLine;
}

export default function HistoryPage() {
  const [runs, setRuns] = useState<HistoryRun[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    setRuns(getHistory());
  }, []);

  function onClear() {
    clearHistory();
    setRuns([]);
    setOpenId(null);
  }

  return (
    <main className="layout" style={{ gridTemplateColumns: "1fr", maxWidth: 860 }}>
      <section className="card">
        <div className="panelHeader">
          <h2 className="panelTitle">RUN HISTORY</h2>
          <button className="pillBtn" type="button" onClick={onClear} disabled={!runs.length}>
            Clear
          </button>
        </div>

        {!runs.length ? (
          <p className="muted">
            No runs yet. Debug sessions run from the home page are saved here automatically, in this browser.
          </p>
        ) : (
          <div className="attemptList">
            {runs.map((run) => (
              <details
                key={run.id}
                className={`attemptCard ${run.result.success ? "attemptCard--success" : "attemptCard--error"}`}
                open={openId === run.id}
                onToggle={(e) => setOpenId(e.currentTarget.open ? run.id : null)}
              >
                <summary>
                  <div className="attemptLeft">
                    <span className="attemptTitle">{codePreview(run.code) || "(empty)"}</span>
                    <span
                      className={`attemptBadge ${run.result.success ? "attemptBadge--success" : "attemptBadge--error"}`}
                    >
                      {run.result.success ? "PASS" : "FAIL"}
                    </span>
                  </div>
                  <span className="attemptMeta">
                    {formatTimestamp(run.timestamp)} · {run.model} · {run.result.attempts_used} attempt(s)
                  </span>
                </summary>
                <div className="attemptBody" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  <ResultSummary result={run.result} />
                  <AttemptTimeline history={run.result.history} maxAttempts={run.maxAttempts} />
                </div>
              </details>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
