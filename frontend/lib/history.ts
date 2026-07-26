import type { DebugResponse } from "@/lib/types";

export type HistoryRun = {
  id: string;
  timestamp: number;
  code: string;
  tests?: string;
  model: string;
  maxAttempts: number;
  timeout: number;
  result: DebugResponse;
};

const STORAGE_KEY = "execfix:history";
const MAX_ENTRIES = 25;

export function getHistory(): HistoryRun[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as HistoryRun[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function addHistoryRun(entry: Omit<HistoryRun, "id" | "timestamp">) {
  if (typeof window === "undefined") return;
  const run: HistoryRun = {
    ...entry,
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: Date.now()
  };
  const next = [run, ...getHistory()].slice(0, MAX_ENTRIES);
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
}

export function clearHistory() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}
