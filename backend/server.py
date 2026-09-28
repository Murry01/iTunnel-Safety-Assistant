# -*- coding: utf-8 -*-
"""
server.py — FastAPI backend for the Tunnel Safety Agent.

Thin HTTP/SSE wrapper around the existing orchestrator/chatstore/tools
modules; no business logic lives here. Run from the project root (the
parent of this backend/ package), not from inside backend/ itself:

    uvicorn backend.server:app --reload --port 8000   # dev
    uvicorn backend.server:app                         # prod, serves frontend/dist too
"""
import json
import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import bilingual, chatstore, config, orchestrator, report
from .tools.query_graph import case_subgraph

CASE_RE = re.compile(r"TA-\d{4}")

class UTF8JSONResponse(JSONResponse):
    """Declare JSON's UTF-8 encoding for older Windows PowerShell clients."""

    media_type = "application/json; charset=utf-8"


app = FastAPI(
    title="Tunnel Safety Agent API",
    default_response_class=UTF8JSONResponse,
)


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    question: str
    history: list[dict] = []
    mode: str | None = None  # accepted for the frontend's fast/deep/strict
    # selector; not yet used to change agent behavior.


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _fetch_cases(case_ids: list[str]) -> list[dict]:
    if not case_ids:
        return []
    con = config.sqlite_conn_readonly()
    try:
        placeholders = ",".join("?" for _ in case_ids)
        cur = con.execute(
            f"SELECT * FROM accidents WHERE case_id IN ({placeholders})", case_ids
        )
        cols = [d[0] for d in cur.description]
        rows = {r[0]: dict(zip(cols, r)) for r in cur.fetchall()}
    finally:
        con.close()
    return [rows[cid] for cid in case_ids if cid in rows]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/documents")
def get_documents():
    """'Knowledge Base' panel content: accident-type categories + glossary
    terms — this system has no source documents, so these stand in for them."""
    con = config.sqlite_conn_readonly()
    try:
        cur = con.execute(
            "SELECT accident_type, COUNT(*), SUM(fatalities) "
            "FROM accidents GROUP BY accident_type ORDER BY 2 DESC"
        )
        categories = [
            {
                "name": accident_type,
                "tag": "ACCIDENT TYPE",
                "meta": f"{count} cases",
                "color": "critical" if fatal else "incident",
            }
            for accident_type, count, fatal in cur.fetchall()
        ]

        cur = con.execute("SELECT ko, en, aliases, category FROM glossary ORDER BY ko")
        glossary = [
            {
                "name": f"{ko} ({en})",
                "tag": (category or "term").upper(),
                "meta": f"{len(json.loads(aliases)) if aliases else 0} aliases",
                "color": "spec",
            }
            for ko, en, aliases, category in cur.fetchall()
        ]
    finally:
        con.close()
    return categories + glossary


@app.get("/api/report/work-processes")
def get_report_work_processes():
    return report.list_work_processes()


@app.get("/api/report")
def get_report(work_process: str, tunnel_type: str | None = None, format: str = "jha"):
    return report.build_report(work_process, tunnel_type or None, format)


@app.get("/api/conversations")
def list_conversations():
    return chatstore.list_conversations()


@app.get("/api/conversations/{conversation_id}/messages")
def get_messages(conversation_id: str):
    return chatstore.load_messages(conversation_id)


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    chatstore.delete_conversation(conversation_id)
    return {"ok": True}


@app.get("/api/cases")
def get_cases(ids: str):
    case_ids = [c for c in ids.split(",") if c]
    return _fetch_cases(case_ids)


@app.get("/api/graph")
def get_graph(case_ids: str):
    ids = [c for c in case_ids.split(",") if c][:5]
    try:
        data = case_subgraph(ids)
    except Exception as e:
        return {"available": False, "error": str(e)}
    nodes = [
        {"id": key, "label": name, "group": label}
        for key, (label, name) in data["nodes"].items()
    ]
    edges = [{"from": s, "to": d, "label": rel} for s, d, rel in data["edges"]]
    return {"available": True, "nodes": nodes, "edges": edges}


@app.post("/api/chat")
def chat(req: ChatRequest):
    def event_stream():
        conv_id = req.conversation_id
        is_new = conv_id is None
        title = None
        if is_new:
            title = chatstore.title_from_text(req.question)
            conv_id = chatstore.create_conversation(title)
        chatstore.append_message(conv_id, "user", req.question)

        yield _sse({"type": "conversation", "conversation_id": conv_id, "title": title})

        answer_text = ""
        charts: list[dict] = []
        try:
            for event in orchestrator.run_agent(req.question, req.history):
                kind = event[0]
                if kind == "status":
                    yield _sse({"type": "status", "text": event[1]})
                elif kind == "tool_call":
                    _, name, args = event
                    yield _sse({"type": "tool_call", "name": name, "args": args})
                elif kind == "tool_result":
                    _, name, count = event
                    yield _sse({"type": "tool_result", "name": name, "count": count})
                elif kind == "chart":
                    charts.append(event[1])
                    yield _sse({"type": "chart", "spec": event[1]})
                elif kind == "delta":
                    answer_text += event[1]
                    yield _sse({"type": "delta", "text": event[1]})
                elif kind == "done":
                    answer_text = event[1] or answer_text
        except Exception as e:
            yield _sse({"type": "error", "text": str(e)})

        case_ids = list(dict.fromkeys(CASE_RE.findall(answer_text)))
        chatstore.append_message(conv_id, "assistant", answer_text, case_ids, charts)
        chatstore.touch(conv_id)

        yield _sse({
            "type": "done", "answer": answer_text, "case_ids": case_ids,
            "conversation_id": conv_id,
        })

        # best-effort, sent after 'done' so it never delays the visible answer
        follow_ups = orchestrator.generate_follow_ups(
            req.question, answer_text, bilingual.detect_language(req.question)
        )
        yield _sse({"type": "follow_ups", "questions": follow_ups})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── production static frontend (after `npm run build`) ────────────
# frontend/ lives at the project root, one level up from this backend/ package
_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
