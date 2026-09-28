/**
 * API layer — the single integration point with the backend.
 *
 * The backend (backend/server.py) streams chat responses over SSE and
 * persists every conversation to chats.db, so this file is a bit richer
 * than a typical single-shot fetch wrapper:
 *
 *   GET    /api/health                          → 200 OK when backend is up
 *   GET    /api/documents                        → [{ name, tag, meta, color }]
 *   GET    /api/conversations                     → [{ id, title, updated_at, ... }]
 *   GET    /api/conversations/{id}/messages       → [{ role, content, case_ids, charts }]
 *   DELETE /api/conversations/{id}
 *   GET    /api/cases?ids=TA-0001,TA-0002         → [{ case_id, narrative, ... }]
 *   GET    /api/graph?case_ids=TA-0001            → { available, nodes, edges }
 *   POST   /api/chat                              → text/event-stream, one JSON
 *                                                    object per `data:` line:
 *     {type:"conversation", conversation_id, title}
 *     {type:"status"|"tool_call"|"tool_result", ...}
 *     {type:"chart", spec}
 *     {type:"delta", text}
 *     {type:"error", text}
 *     {type:"done", answer, case_ids, conversation_id}
 *
 * If the backend is unreachable, the UI falls back to demo mode so the
 * frontend remains fully browsable during development.
 */
import { fetchEventSource } from "@microsoft/fetch-event-source";

const API_BASE = import.meta.env.VITE_API_BASE || "";

export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchDocuments() {
  const res = await fetch(`${API_BASE}/api/documents`);
  if (!res.ok) throw new Error(`Backend error ${res.status}`);
  return res.json();
}

export async function listConversations() {
  const res = await fetch(`${API_BASE}/api/conversations`);
  if (!res.ok) throw new Error(`Backend error ${res.status}`);
  return res.json();
}

export async function loadMessages(conversationId) {
  const res = await fetch(`${API_BASE}/api/conversations/${conversationId}/messages`);
  if (!res.ok) throw new Error(`Backend error ${res.status}`);
  return res.json();
}

export async function deleteConversationRequest(conversationId) {
  const res = await fetch(`${API_BASE}/api/conversations/${conversationId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Backend error ${res.status}`);
}

export async function fetchCases(caseIds) {
  if (!caseIds || caseIds.length === 0) return [];
  const res = await fetch(`${API_BASE}/api/cases?ids=${encodeURIComponent(caseIds.join(","))}`);
  if (!res.ok) throw new Error(`Backend error ${res.status}`);
  return res.json();
}

export async function fetchGraph(caseIds) {
  const res = await fetch(`${API_BASE}/api/graph?case_ids=${encodeURIComponent(caseIds.join(","))}`);
  if (!res.ok) throw new Error(`Backend error ${res.status}`);
  return res.json();
}

export async function fetchWorkProcesses() {
  const res = await fetch(`${API_BASE}/api/report/work-processes`);
  if (!res.ok) throw new Error(`Backend error ${res.status}`);
  return res.json();
}

/** Deterministic, non-LLM Prevention Report — see backend/report.py. */
export async function generateReport({ workProcess, tunnelType, format }) {
  const params = new URLSearchParams({ work_process: workProcess, format });
  if (tunnelType) params.set("tunnel_type", tunnelType);
  const res = await fetch(`${API_BASE}/api/report?${params.toString()}`);
  if (!res.ok) throw new Error(`Backend error ${res.status}`);
  return res.json();
}

/**
 * Stream a chat turn. `onEvent` is called once per SSE event (see the
 * shapes documented above). Resolves when the stream ends; rejects on
 * network failure or non-OK response. Pass `signal` from an AbortController
 * to support a Stop button — aborting rejects with `err.name === "AbortError"`.
 */
export function streamChat({ message, mode, conversationId, history }, onEvent, signal) {
  return fetchEventSource(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: message,
      mode,
      conversation_id: conversationId,
      history,
    }),
    signal,
    openWhenHidden: true,
    async onopen(res) {
      if (!res.ok) throw new Error(`Backend error ${res.status}`);
    },
    onmessage(ev) {
      onEvent(JSON.parse(ev.data));
    },
    onerror(err) {
      // one-shot request/response stream, not a subscription — rethrow so
      // fetch-event-source stops its default infinite retry loop
      throw err;
    },
  });
}

/** Demo reply used when the backend is offline. */
export function demoReply(mode) {
  return new Promise((resolve) =>
    setTimeout(
      () =>
        resolve({
          text:
            "**Demo mode** — the backend at `" +
            (API_BASE || "/api") +
            "` is not reachable, so this is a placeholder response.\n\nStart your backend server and refresh, and answers will be generated from your indexed knowledge base with full reasoning traces and citations.",
          steps: [
            `Selected retrieval strategy for ${mode} mode.`,
            "Attempted to reach the backend API.",
            "Fell back to demo response (backend offline).",
          ],
          sources: [],
          riskLevel: null,
        }),
      900
    )
  );
}
