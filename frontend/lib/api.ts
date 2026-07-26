import { getSettings } from "@/lib/settings";
import type { DebugResponse, EvalResponse } from "@/lib/types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const apiBase = getSettings().apiBase;
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API ${response.status}: ${text}`);
  }

  return (await response.json()) as T;
}

export async function runDebug(payload: {
  code: string;
  tests?: string;
  max_attempts: number;
  timeout: number;
  model?: string;
}): Promise<DebugResponse> {
  return request<DebugResponse>("/debug", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function runEval(payload: {
  model?: string;
  max_attempts: number;
  timeout: number;
  limit?: number;
  only?: string[];
}): Promise<EvalResponse> {
  return request<EvalResponse>("/eval/run", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

