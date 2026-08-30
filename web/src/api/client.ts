import { withBase } from "../base";
import type { CreateGenerationResponse, StreamEvent } from "../types/generation";
import type { AppStatus, ReadyStatus } from "../types/status";

async function getJson<T>(path: string): Promise<T> {
  const url = withBase(path);
  const res = await fetch(url, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`${url} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

export function fetchStatus(): Promise<AppStatus> {
  return getJson<AppStatus>("/api/status");
}

export function fetchReady(): Promise<ReadyStatus> {
  return getJson<ReadyStatus>("/api/readyz");
}

export function fetchHealth(): Promise<{ status: string; version: string }> {
  return getJson("/api/healthz");
}

export async function createGeneration(body: {
  prompt: string;
  seed?: number;
  max_new_tokens?: number;
}): Promise<CreateGenerationResponse> {
  const url = withBase("/api/generations");
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (res.status === 409) {
    const detail = (await res.json().catch(() => null)) as
      | { detail?: { message?: string; error?: string } }
      | null;
    const message =
      detail?.detail?.message ?? "A generation is already running. Stop it or wait.";
    const err = new Error(message) as Error & { code?: string };
    err.code = "busy";
    throw err;
  }
  if (!res.ok) {
    throw new Error(`${url} failed: ${res.status}`);
  }
  return (await res.json()) as CreateGenerationResponse;
}

export async function stopGeneration(generationId: string): Promise<void> {
  const url = withBase(`/api/generations/${encodeURIComponent(generationId)}/stop`);
  const res = await fetch(url, {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  if (!res.ok && res.status !== 404) {
    throw new Error(`${url} failed: ${res.status}`);
  }
}

/** Open a generation event stream; replays from afterSeq on reconnect. */
export function openGenerationStream(
  generationId: string,
  afterSeq: number,
  handlers: {
    onEvent: (event: StreamEvent) => void;
    onError?: (error: Event) => void;
    onClose?: () => void;
  },
): { close: () => void } {
  const base = withBase(
    `/api/generations/${encodeURIComponent(generationId)}/stream?after_seq=${afterSeq}`,
  );
  // Prefer same-origin relative WS
  const wsUrl = (() => {
    if (base.startsWith("http://") || base.startsWith("https://")) {
      const u = new URL(base);
      u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
      return u.toString();
    }
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}${base}`;
  })();

  let closed = false;
  let ws: WebSocket | null = null;
  let reconnectTimer: number | null = null;
  let lastSeq = afterSeq;
  let intentionalClose = false;

  const connect = () => {
    if (closed) return;
    const url = wsUrl.replace(/after_seq=\d+/, `after_seq=${lastSeq}`);
    ws = new WebSocket(url);
    ws.onmessage = (msg) => {
      try {
        const event = JSON.parse(String(msg.data)) as StreamEvent;
        if (typeof event.seq === "number" && event.seq > lastSeq) {
          lastSeq = event.seq;
        }
        // Ignore keepalives for UI state machine, but still advance seq.
        if (event.type === "warning" && event.message === "keepalive") {
          return;
        }
        handlers.onEvent(event);
      } catch {
        // ignore malformed frames
      }
    };
    ws.onerror = (ev) => {
      handlers.onError?.(ev);
    };
    ws.onclose = () => {
      handlers.onClose?.();
      if (!intentionalClose && !closed) {
        // Brief reconnect for transient drops (LDW-006).
        reconnectTimer = window.setTimeout(connect, 400);
      }
    };
  };

  connect();

  return {
    close: () => {
      closed = true;
      intentionalClose = true;
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }
      ws?.close();
    },
  };
}
