"use client";

import { useEffect, useState } from "react";

import { DEFAULT_SETTINGS, getSettings, resetSettings, saveSettings, type Settings } from "@/lib/settings";
import { clearHistory, getHistory } from "@/lib/history";

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [saved, setSaved] = useState(false);
  const [historyCount, setHistoryCount] = useState(0);

  useEffect(() => {
    setSettings(getSettings());
    setHistoryCount(getHistory().length);
  }, []);

  function onSave() {
    saveSettings(settings);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  }

  function onReset() {
    resetSettings();
    setSettings(DEFAULT_SETTINGS);
  }

  function onClearHistory() {
    clearHistory();
    setHistoryCount(0);
  }

  return (
    <main className="layout" style={{ gridTemplateColumns: "1fr", maxWidth: 640 }}>
      <section className="card">
        <div className="panelHeader">
          <h2 className="panelTitle">CONNECTION</h2>
        </div>
        <div className="row" style={{ marginBottom: 14 }}>
          <div style={{ flex: 1 }}>
            <label htmlFor="api-base">Backend API base URL</label>
            <input
              id="api-base"
              value={settings.apiBase}
              onChange={(e) => setSettings((s) => ({ ...s, apiBase: e.target.value }))}
              spellCheck={false}
            />
          </div>
        </div>

        <div className="panelHeader" style={{ marginTop: 20 }}>
          <h2 className="panelTitle">DEFAULTS</h2>
        </div>
        <div className="row" style={{ marginBottom: 14, gap: 12 }}>
          <div style={{ flex: 1, minWidth: 180 }}>
            <label htmlFor="default-model">Default model</label>
            <input
              id="default-model"
              value={settings.defaultModel}
              onChange={(e) => setSettings((s) => ({ ...s, defaultModel: e.target.value }))}
              spellCheck={false}
            />
          </div>
          <div style={{ width: 160 }}>
            <label htmlFor="default-attempts">Default max attempts</label>
            <input
              id="default-attempts"
              type="number"
              min={1}
              max={10}
              value={settings.defaultMaxAttempts}
              onChange={(e) => setSettings((s) => ({ ...s, defaultMaxAttempts: Number(e.target.value) }))}
            />
          </div>
          <div style={{ width: 160 }}>
            <label htmlFor="default-timeout">Default timeout (s)</label>
            <input
              id="default-timeout"
              type="number"
              min={1}
              max={120}
              value={settings.defaultTimeout}
              onChange={(e) => setSettings((s) => ({ ...s, defaultTimeout: Number(e.target.value) }))}
            />
          </div>
        </div>

        <div className="row" style={{ gap: 10, alignItems: "center" }}>
          <button className="runBtn" type="button" onClick={onSave}>
            {saved ? "Saved" : "Save settings"}
          </button>
          <button className="pillBtn" type="button" onClick={onReset}>
            Reset to defaults
          </button>
        </div>
      </section>

      <section className="card" style={{ marginTop: 16 }}>
        <div className="panelHeader">
          <h2 className="panelTitle">LOCAL DATA</h2>
        </div>
        <p className="muted" style={{ fontSize: 13, marginBottom: 12 }}>
          {historyCount} run{historyCount === 1 ? "" : "s"} stored in this browser.
        </p>
        <button className="pillBtn" type="button" onClick={onClearHistory} disabled={historyCount === 0}>
          Clear run history
        </button>
      </section>
    </main>
  );
}
