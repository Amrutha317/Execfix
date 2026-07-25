import type { Monaco } from "@monaco-editor/react";

/** GitHub-dark–aligned editor colors (Python + general). */
export function setupGithubDarkTheme(monaco: Monaco) {
  monaco.editor.defineTheme("github-dark-custom", {
    base: "vs-dark",
    inherit: true,
    rules: [
      { token: "comment", foreground: "8b949e", fontStyle: "italic" },
      { token: "keyword", foreground: "ff7b72" },
      { token: "keyword.control", foreground: "ff7b72" },
      { token: "keyword.operator", foreground: "ff7b72" },
      { token: "number", foreground: "79c0ff" },
      { token: "number.hex", foreground: "79c0ff" },
      { token: "string", foreground: "a5d6ff" },
      { token: "string.escape", foreground: "a5d6ff" },
      { token: "regexp", foreground: "a5d6ff" },
      { token: "type.identifier", foreground: "d2a8ff" },
      { token: "namespace", foreground: "d2a8ff" },
      { token: "type", foreground: "d2a8ff" },
      { token: "delimiter", foreground: "e6edf3" },
      { token: "delimiter.bracket", foreground: "e6edf3" },
      { token: "identifier", foreground: "e6edf3" },
      { token: "tag", foreground: "ff7b72" },
      { token: "metatag", foreground: "ff7b72" },
      { token: "annotation", foreground: "ff7b72" },
      { token: "predefined", foreground: "d2a8ff" }
    ],
    colors: {
      "editor.background": "#0d1117",
      "editor.foreground": "#e6edf3",
      "editorLineNumber.foreground": "#484f58",
      "editorLineNumber.activeForeground": "#8b949e",
      "editorCursor.foreground": "#58a6ff",
      "editor.selectionBackground": "#264f78",
      "editor.inactiveSelectionBackground": "#264f7844",
      "editor.lineHighlightBackground": "#161b2200",
      "editorLineHighlightBorder": "#30363d",
      "editorIndentGuide.background": "#21262d",
      "editorIndentGuide.activeBackground": "#30363d",
      "scrollbarSlider.background": "#484f5833",
      "scrollbarSlider.hoverBackground": "#484f5888",
      "scrollbarSlider.activeBackground": "#484f58aa"
    }
  });
}
