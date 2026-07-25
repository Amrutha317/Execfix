"use client";

import type { HistoryEntry } from "@/lib/types";

function patchBody(text: string) {
  const lines = text.split("\n");
  const looksLikeDiff = lines.some((l) => l.startsWith("-") || l.startsWith("+"));
  if (!looksLikeDiff) {
    return <pre>{text}</pre>;
  }
  return (
    <div className="patchPre">
      {lines.map((line, i) => {
        if (line.startsWith("-")) {
          return (
            <div key={i} className="diffLineRemoved">
              {line}
            </div>
          );
        }
        if (line.startsWith("+")) {
          return (
            <div key={i} className="diffLineAdded">
              {line}
            </div>
          );
        }
        return <div key={i}>{line}</div>;
      })}
    </div>
  );
}

function cardClass(entry: HistoryEntry) {
  if (entry.success) return "attemptCard attemptCard--success";
  if (entry.llm_output) return "attemptCard attemptCard--patching";
  if (entry.exception_type || entry.error) return "attemptCard attemptCard--error";
  return "attemptCard";
}

function badgeClass(entry: HistoryEntry) {
  if (entry.success) return "attemptBadge attemptBadge--success";
  if (entry.llm_output) return "attemptBadge attemptBadge--patching";
  if (entry.exception_type || entry.error) return "attemptBadge attemptBadge--error";
  return "attemptBadge";
}

function badgeLabel(entry: HistoryEntry) {
  if (entry.success) return "PASS";
  if (entry.llm_output) return "Patching...";
  return entry.exception_type ?? "FAIL";
}

export default function AttemptTimeline({
  history,
  maxAttempts
}: {
  history: HistoryEntry[];
  maxAttempts: number;
}) {
  const subtitle =
    history.length && maxAttempts > 0
      ? `attempt ${history.length} of ${maxAttempts}`
      : maxAttempts > 0
        ? `0 of ${maxAttempts}`
        : "";

  return (
    <>
      <div className="panelHeader" style={{ marginTop: 0 }}>
        <h2 className="panelTitle">ATTEMPT TIMELINE</h2>
        <span className="muted" style={{ fontSize: 12 }}>
          {subtitle}
        </span>
      </div>
      {!history.length ? (
        <p className="muted">No attempts yet. Run debug to see the timeline.</p>
      ) : (
        <div className="attemptList">
          {history.map((entry, idx) => (
            <details key={idx} className={cardClass(entry)} open>
              <summary>
                <div className="attemptLeft">
                  <span className="attemptTitle">Attempt {entry.attempt ?? idx + 1}</span>
                  <span className={badgeClass(entry)}>{badgeLabel(entry)}</span>
                </div>
                <span className="attemptMeta">{((entry.duration_ms ?? 0) / 1000).toFixed(1)}s</span>
              </summary>
              <div className="attemptBody">
                {entry.error ? <p className="attemptErrorLine">{entry.error.split("\n")[0]}</p> : null}
                <div className="attemptSub">{entry.llm_output ? "PROPOSED PATCH" : "DETAIL"}</div>
                {entry.llm_output ? patchBody(entry.llm_output) : <pre>{entry.code ?? ""}</pre>}
              </div>
            </details>
          ))}
        </div>
      )}
    </>
  );
}
