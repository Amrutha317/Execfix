import type { DebugResponse, EvalResponse } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
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

