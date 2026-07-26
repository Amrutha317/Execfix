import { getSettings } from "@/lib/settings";
import type { DebugResponse, EvalResponse, HistoryEntry } from "@/lib/types";

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

type StreamAttemptEvent = { type: "attempt"; entry: HistoryEntry };
type StreamDoneEvent = { type: "done" } & DebugResponse;
type StreamErrorEvent = { type: "error"; detail: string };
type StreamEvent = StreamAttemptEvent | StreamDoneEvent | StreamErrorEvent;

export async function streamDebug(
  payload: {
    code: string;
    tests?: string;
    max_attempts: number;
    timeout: number;
    model?: string;
  },
  handlers: {
    onAttempt: (entry: HistoryEntry) => void;
    onDone: (result: DebugResponse) => void;
    onError: (message: string) => void;
  }
): Promise<void> {
  const apiBase = getSettings().apiBase;
  const response = await fetch(`${apiBase}/debug/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store"
  });

  if (!response.ok || !response.body) {
    const text = await response.text().catch(() => "");
    handlers.onError(`API ${response.status}: ${text}`);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let frameBreak = buffer.indexOf("\n\n");
    while (frameBreak !== -1) {
      const frame = buffer.slice(0, frameBreak);
      buffer = buffer.slice(frameBreak + 2);
      frameBreak = buffer.indexOf("\n\n");

      const dataLine = frame.split("\n").find((line) => line.startsWith("data: "));
      if (!dataLine) continue;

      const event = JSON.parse(dataLine.slice("data: ".length)) as StreamEvent;
      if (event.type === "attempt") {
        handlers.onAttempt(event.entry);
      } else if (event.type === "done") {
        const { type, ...result } = event;
        void type;
        handlers.onDone(result);
      } else {
        handlers.onError(event.detail);
      }
    }
  }
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

