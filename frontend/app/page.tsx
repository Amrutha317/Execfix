"use client";

import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

import AttemptTimeline from "@/components/attempt-timeline";
import CodeEditor from "@/components/code-editor";
import ResultSummary from "@/components/result-summary";
import { runDebug } from "@/lib/api";
import { EXAMPLE_CODE, EXAMPLE_RESULT } from "@/lib/example-run";
import { addHistoryRun } from "@/lib/history";
import { getSettings } from "@/lib/settings";
import type { DebugResponse } from "@/lib/types";

function totalElapsedMs(result: DebugResponse | null) {
  if (!result?.history?.length) return null;
  return result.history.reduce((acc, h) => acc + (h.duration_ms ?? 0), 0);
}

export default function DebugPage() {
  const [code, setCode] = useState(EXAMPLE_CODE);
  const [tests, setTests] = useState("");
  const [maxAttempts, setMaxAttempts] = useState(3);
  const [timeout, setTimeoutSeconds] = useState(10);
  const [model, setModel] = useState("gpt-5-mini");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DebugResponse | null>(null);
  const [actionsHost, setActionsHost] = useState<HTMLElement | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [runningElapsedMs, setRunningElapsedMs] = useState(0);

  useEffect(() => {
    setActionsHost(document.getElementById("topbar-actions"));
    const settings = getSettings();
    setModel(settings.defaultModel);
    setMaxAttempts(settings.defaultMaxAttempts);
    setTimeoutSeconds(settings.defaultTimeout);
  }, []);

  useEffect(() => {
    if (!loading) return;
    const start = Date.now();
    setRunningElapsedMs(0);
    const id = setInterval(() => setRunningElapsedMs(Date.now() - start), 200);
    return () => clearInterval(id);
  }, [loading]);

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
              <button
                type="button"
                className="metaPill metaPill--interactive"
                title="Click to change model, attempts, and timeout"
                aria-expanded={settingsOpen}
                onClick={() => setSettingsOpen((o) => !o)}
              >
                {model} · {maxAttempts} attempts · {timeout}s
                <span className={`metaPill__chevron ${settingsOpen ? "metaPill__chevron--open" : ""}`} aria-hidden>
                  ▾
                </span>
              </button>
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
                <button className="pillBtn" type="button" onClick={() => setCode(EXAMPLE_CODE)}>
                  Load example
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
          {loading ? (
            <div className="runningCard">
              <span className="runningCard__pulse" aria-hidden />
              Running attempt... {(runningElapsedMs / 1000).toFixed(1)}s
            </div>
          ) : result ? (
            <ResultSummary result={result} />
          ) : (
            <>
              <span className="examplePill" style={{ marginBottom: 6, display: "inline-block", width: "fit-content" }}>
                EXAMPLE
              </span>
              <ResultSummary result={EXAMPLE_RESULT} />
            </>
          )}
          <div style={{ flex: 1, minHeight: 0 }}>
            {loading ? (
              <>
                <div className="panelHeader" style={{ marginTop: 0 }}>
                  <h2 className="panelTitle">ATTEMPT TIMELINE</h2>
                </div>
                <p className="muted">Waiting for the first attempt to finish...</p>
              </>
            ) : (
              <AttemptTimeline
                history={(result ?? EXAMPLE_RESULT).history}
                maxAttempts={maxAttempts}
                isExample={!result}
              />
            )}
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

      {settingsOpen ? (
        <div className="settingsDrawer settingsDrawer--open">
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
        </div>
      ) : null}
    </>
  );
}
