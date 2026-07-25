"use client";

import dynamic from "next/dynamic";
import { useCallback } from "react";
import type { Monaco } from "@monaco-editor/react";

import { setupGithubDarkTheme } from "@/lib/github-monaco-theme";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

type Props = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  rows?: number;
};

const FONT_STACK = "'JetBrains Mono', 'Fira Code', Consolas, monospace";

export default function CodeEditor({ label, value, onChange, rows = 16 }: Props) {
  const lineHeightPx = Math.round(12 * 1.7);
  const heightPx = Math.max(96, rows * lineHeightPx + 16);

  const beforeMount = useCallback((monaco: Monaco) => {
    setupGithubDarkTheme(monaco);
  }, []);

  return (
    <div>
      {label ? <div className="codeEditorLabel">{label}</div> : null}
      <div className="codeEditorChrome">
        <MonacoEditor
          height={heightPx}
          language="python"
          theme="github-dark-custom"
          value={value}
          beforeMount={beforeMount}
          onChange={(v) => onChange(v ?? "")}
          options={{
            minimap: { enabled: false },
            fontSize: 12,
            lineHeight: lineHeightPx,
            wordWrap: "on",
            scrollBeyondLastLine: false,
            fontFamily: FONT_STACK,
            fontLigatures: true,
            padding: { top: 8, bottom: 8 },
            lineNumbersMinChars: 2,
            folding: true,
            glyphMargin: false,
            overviewRulerBorder: false,
            overviewRulerLanes: 0,
            hideCursorInOverviewRuler: true,
            scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
            renderLineHighlight: "line",
            contextmenu: false,
            automaticLayout: true
          }}
        />
      </div>
    </div>
  );
}
