# Tunnel Safety Agent — Frontend

A production-ready React frontend for the Tunnel Safety Agent. Built with **Vite + React 18 + Tailwind CSS**, with markdown rendering, agent reasoning traces, risk banners, and source citations.

## Quick start

```bash
npm install
npm run dev        # http://localhost:3000
```

Without a backend running, the app works in **demo mode** (the status dot next to your name in the sidebar shows grey). When your backend is reachable, the dot turns green and all answers come from it.

```bash
npm run build      # production build → dist/
npm run preview    # serve the production build locally
```

## Connecting your backend

The frontend talks to the backend through **one file**: `src/api.js`. Everything else is UI.

### 1. Expected HTTP contract

Expose these three endpoints from your backend (wrap your existing CLI logic in a small HTTP server — example below):

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | Returns 200 when the backend is up (drives the green status dot) |
| `/api/chat` | POST | Main Q&A endpoint |
| `/api/documents` | GET | Lists indexed documents for the Knowledge base panel |

**`POST /api/chat` request:**

```json
{
  "message": "Verify rib spacing for RMR 30-40",
  "mode": "deep",
  "conversation_id": "c-1712345678",
  "history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

**`POST /api/chat` response** (only `answer` is required — the UI hides anything missing):

```json
{
  "answer": "Markdown-formatted answer …",
  "steps": ["Retrieved rock-mass tables …", "Matched RMR band …"],
  "sources": [
    { "doc": "NATM Design Guideline Rev. 4.pdf", "section": "§6.3", "snippet": "For RMR 30-40 …" }
  ],
  "risk_level": "critical"
}
```

`risk_level` accepts `"critical"`, `"warn"`, or `null` and renders the amber safety banner.

**`GET /api/documents` response:**

```json
[
  { "name": "NATM Design Guideline Rev. 4.pdf", "tag": "DESIGN SPEC", "meta": "89 pages", "color": "spec" }
]
```

`color` is one of `critical` (amber), `spec` (cyan), `incident` (grey).

If your backend already returns differently named fields, don't change the backend — adjust `mapResponse()` in `src/api.js` (it already accepts `answer`/`response`/`text` and `doc`/`document`/`file` variants).

### 2. Wrapping a Python CLI backend (FastAPI example)

If your RAG pipeline currently runs as a CLI script, expose it with FastAPI:

```python
# server.py  —  pip install fastapi uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# from your_pipeline import answer_query   # your existing RAG entry point

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    mode: str = "deep"
    conversation_id: str | None = None
    history: list[dict] = []

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/chat")
def chat(req: ChatRequest):
    # result = answer_query(req.message, mode=req.mode, history=req.history)
    return {
        "answer": "…",        # result.answer
        "steps": [],           # result.trace
        "sources": [],         # result.citations
        "risk_level": None,
    }

@app.get("/api/documents")
def documents():
    return []  # list your indexed docs

# uvicorn server:app --port 8000
```

### 3. Pointing the frontend at the backend

- **Development:** the Vite dev server proxies `/api/*` to `http://localhost:8000` (see `vite.config.js`). Change the target or set `VITE_BACKEND_URL` if your backend runs elsewhere.
- **Production:** either serve `dist/` from the same server as the API (same-origin `/api` just works), or copy `.env.example` to `.env` and set `VITE_API_BASE=https://your-backend.example.com` before building.

## Project structure

```
src/
  api.js                    ← backend integration (the only file you need to touch)
  App.jsx                   ← state + wiring
  data/demo.js              ← seed conversations & docs for demo mode
  components/
    Sidebar.jsx             ← nav, recents, profile, backend status dot
    TopBar.jsx              ← mode selector (Fast / Deep Reasoning / Safety-Strict)
    Composer.jsx            ← auto-growing input, Enter-to-send, Shift+Enter newline
    MessageBubble.jsx       ← messages, agent trace, risk banner, citations, actions
    Panels.jsx              ← welcome screen, knowledge base panel, search modal
    Icons.jsx               ← SVG icon set
tailwind.config.js          ← full design token system (colors, fonts, animations)
```

## Features

- Markdown rendering in answers (headings, lists, tables, code blocks)
- Collapsible agent reasoning traces and horizontally scrolling citation cards
- Amber risk banners driven by `risk_level` from the backend
- Regenerate last answer, copy-with-feedback, thumbs voting
- Chat search (⌘-palette style), collapsible sidebar, knowledge base panel
- Live backend health indicator with automatic demo-mode fallback
- Graceful inline error messages when a request fails
