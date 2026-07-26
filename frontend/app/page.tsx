"use client";

import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

import AttemptTimeline from "@/components/attempt-timeline";
import CodeEditor from "@/components/code-editor";
import ResultSummary from "@/components/result-summary";
import { runDebug } from "@/lib/api";
import { addHistoryRun } from "@/lib/history";
import { getSettings } from "@/lib/settings";
import type { DebugResponse } from "@/lib/types";

const DEFAULT_CODE = `def get_item(items, index):
    return items[index]

get_item([1, 2, 3], 10)
`;

function totalElapsedMs(result: DebugResponse | null) {
  if (!result?.history?.length) return null;
  return result.history.reduce((acc, h) => acc + (h.duration_ms ?? 0), 0);
}

export default function DebugPage() {
  const [code, setCode] = useState(DEFAULT_CODE);
  const [tests, setTests] = useState("");
  const [maxAttempts, setMaxAttempts] = useState(3);
  const [timeout, setTimeoutSeconds] = useState(10);
  const [model, setModel] = useState("gpt-5-mini");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DebugResponse | null>(null);
  const [actionsHost, setActionsHost] = useState<HTMLElement | null>(null);

  useEffect(() => {
    setActionsHost(document.getElementById("topbar-actions"));
    const settings = getSettings();
    setModel(settings.defaultModel);
    setMaxAttempts(settings.defaultMaxAttempts);
    setTimeoutSeconds(settings.defaultTimeout);
  }, []);

  const elapsedLabel = useMemo(() => {
    const ms = totalElapsedMs(result);
    if (ms == null) return "—";
    return `${(ms / 1000).toFixed(1)}s`;
  }, [result]);

  const progressPercent = useMemo(() => {
    if (!maxAttempts) return 0;
    if (loading || !result) return 0;
    return Math.min(100, (result.attempts_used / maxAttempts) * 100);
  }, [loading, result, maxAttempts]);

  async function onRun() {
    setLoading(true);
    setError(null);
    try {
      const response = await runDebug({
        code,
        tests: tests.trim() || undefined,
        max_attempts: maxAttempts,
        timeout,
        model: model.trim() || undefined
      });
      setResult(response);
      addHistoryRun({
        code,
        tests: tests.trim() || undefined,
        model: model.trim() || "default",
        maxAttempts,
        timeout,
        result: response
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {actionsHost
        ? createPortal(
            <div className="topbarActions">
              <div className="metaPill" title="Model, attempts, and timeout for this run">
                {model} · {maxAttempts} attempts · {timeout}s
              </div>
              <button className="runBtn" type="button" onClick={onRun} disabled={loading}>
                <span className="runBtn__pulseDot" aria-hidden />
                {loading ? "Running..." : "Run debug"}
              </button>
            </div>,
            actionsHost
          )
        : null}

      <main className="layout">
        <section className="card splitY" style={{ minHeight: 640 }}>
          <div>
            <div className="panelHeader">
              <h2 className="panelTitle">SOURCE</h2>
              <div className="pillGroup">
                <button type="button" className="pillBtn pillBtn--active" disabled aria-pressed="true">
                  Python
                </button>
                <button
                  className="pillBtn"
                  type="button"
                  onClick={async () => {
                    try {
                      const text = await navigator.clipboard.readText();
                      if (text) setCode(text);
                    } catch {
                      /* clipboard permission */
                    }
                  }}
                >
                  Paste
                </button>
                <button className="pillBtn" type="button" onClick={() => setCode("")}>
                  Clear
                </button>
              </div>
            </div>
            <CodeEditor label="" value={code} onChange={setCode} rows={16} />
          </div>

          <div className="stackedPanel">
            <div className="panelHeader" style={{ marginBottom: 10 }}>
              <h2 className="panelTitle">TEST HARNESS</h2>
              <span className="optionalPill">optional</span>
            </div>
            <CodeEditor
              label=""
              value={tests}
              onChange={setTests}
              rows={4}
              placeholder={
                "# Plain Python, appended after the code on the left and run in the\n" +
                "# same file. Reference your functions/classes directly:\n" +
                "assert get_item([1, 2, 3], 1) == 2"
              }
            />
          </div>
        </section>

        <section className="card resultsCard" style={{ minHeight: 640, display: "flex", flexDirection: "column", gap: 14 }}>
          <div className="panelHeader" style={{ marginBottom: 0 }}>
            <h2 className="panelTitle">RESULT</h2>
          </div>
          {result ? (
            <ResultSummary result={result} />
          ) : (
            <p className="muted" style={{ margin: 0, fontSize: 13 }}>
              Run debug to see the outcome here.
            </p>
          )}
          <div style={{ flex: 1, minHeight: 0 }}>
            <AttemptTimeline history={result?.history ?? []} maxAttempts={maxAttempts} />
          </div>
          {error ? (
            <p className="error" style={{ margin: 0, fontSize: 14 }}>
              {error}
            </p>
          ) : null}
        </section>
      </main>

      <div className="progressWrap" aria-hidden={progressPercent === 0}>
        <div className="progressTrack">
          <div className="progressFill" style={{ width: `${progressPercent}%` }} />
        </div>
      </div>

      <footer className="pageFooter" aria-label="Run metadata">
        <div className="footerPair">
          <span className="footerLabel">Model</span>
          <span className="footerValue">{model}</span>
        </div>
        <div className="footerPair">
          <span className="footerLabel">Tokens</span>
          <span className="footerValue">—</span>
        </div>
        <div className="footerPair">
          <span className="footerLabel">Elapsed</span>
          <span className="footerValue">{elapsedLabel}</span>
        </div>
      </footer>

      <details className="settingsDrawer">
        <summary>Run settings</summary>
        <div className="settingsBody">
          <div className="row">
            <div style={{ flex: 1, minWidth: 220 }}>
              <label htmlFor="model-input">Model</label>
              <select id="model-input" value={model} onChange={(e) => setModel(e.target.value)}>
                <option value="gpt-5-mini">gpt-5-mini</option>
              </select>
            </div>
            <div style={{ width: 160 }}>
              <label htmlFor="max-attempts">Max attempts</label>
              <input
                id="max-attempts"
                type="number"
                min={1}
                max={10}
                value={maxAttempts}
                onChange={(e) => setMaxAttempts(Number(e.target.value))}
              />
            </div>
            <div style={{ width: 160 }}>
              <label htmlFor="timeout-s">Timeout (s)</label>
              <input
                id="timeout-s"
                type="number"
                min={1}
                max={120}
                value={timeout}
                onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
              />
            </div>
          </div>
        </div>
      </details>
    </>
  );
}
