export type Settings = {
  apiBase: string;
  defaultModel: string;
  defaultMaxAttempts: number;
  defaultTimeout: number;
};

const STORAGE_KEY = "execfix:settings";

export const DEFAULT_SETTINGS: Settings = {
  apiBase: process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000",
  defaultModel: "gpt-5-mini",
  defaultMaxAttempts: 3,
  defaultTimeout: 10
};

export function getSettings(): Settings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function saveSettings(settings: Settings) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

export function resetSettings() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}
