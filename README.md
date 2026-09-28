# construction_rag — ingestion scripts

Research evaluation: see [eval/README.md](eval/README.md) for the current RQ1–RQ4
workflow and [eval/STATUS.md](eval/STATUS.md) for completed checks and blockers.
The July evaluation files are pilot results, not final manuscript evidence.

GitHub, Docker, CI/CD, and web deployment instructions are in
[DEPLOYMENT.md](DEPLOYMENT.md).

Builds the three stores for the Tunnel Accident Prevention Assistant
from `Tunnel_data_master.csv` (place it in the project root, next to
`ingestion\`, unless you pass an explicit path). All four scripts live under
`ingestion\` as plain sibling-import scripts — run them with
`python ingestion\<script>.py` from the project root, same as before.

## Setup (PowerShell, inside your venv)

```powershell
venv\Scripts\Activate
pip install -r requirements.txt
```

Credentials — copy `.env.template` to `.env` and fill in your values:

```powershell
Copy-Item .env.template .env
notepad .env
```

All scripts auto-load `.env` (via python-dotenv). Alternatively, plain
environment variables still work:

```powershell
$env:OPENAI_API_KEY = "sk-..."
```

Add `.env` to your `.gitignore` — never commit credentials.

## Run order (from the project root)

```powershell
python ingestion\build_sqlite.py      # 1. accidents.db  (accidents + glossary tables) — no API needed
python ingestion\build_lancedb.py     # 2. ./lancedb/    (embeds 310 docs, ~1-2 min, small API cost)
# Legacy command retained for reference; intentionally disabled because it
# does not explicitly authorize replacement:
# python "ingestion\build_neo4j.py"
python "ingestion\build_neo4j.py" --replace  # 3. Neo4j (DELETES and rebuilds the configured graph)
```

The SQLite and LanceDB scripts are idempotent. `build_neo4j.py` requires the
explicit `--replace` flag because it clears the target graph before ingesting.
Point it at a dedicated research database, not one shared with other projects.

All three read the CSV through `ingestion\common.py`, which renames Korean
headers to English identifiers and validates `case_id` uniqueness. The three
scripts import it as a plain sibling module (`from common import ...`) —
that resolves correctly as long as you invoke them as `python
ingestion\<script>.py`, since Python puts a script's own directory on
`sys.path` automatically.

## Expected verification output

- SQLite : 310 rows, 10 accident types, 25 starter glossary terms
- LanceDB: 310 rows, FTS index on `text`, hybrid smoke test returns 3 case_ids
- Neo4j  : 310 Accident nodes, 10 AccidentType, 4 TunnelType, edges = 310 per type

## Files

| file                       | builds                | needs                 |
|----------------------------|------------------------|-----------------------|
| ingestion\common.py        | (shared loader)       | pandas                |
| ingestion\build_sqlite.py  | accidents.db          | stdlib sqlite3        |
| ingestion\build_lancedb.py | ./lancedb/accidents   | lancedb, openai       |
| ingestion\build_neo4j.py   | Neo4j graph           | neo4j driver          |



# Tunnel Accident Prevention Assistant — agent + backend

## Layout (place next to your stores)
```
construction_rag\
├── accidents.db          <- from ingestion\build_sqlite.py
├── chats.db              <- conversation history, created automatically
├── lancedb\              <- from ingestion\build_lancedb.py
├── .env                  <- shared by ingestion\ and backend\ (OpenAI + Neo4j)
├── ingestion\            <- one-off data-build scripts (see top of this file)
│   ├── common.py  build_sqlite.py  build_lancedb.py  build_neo4j.py
└── backend\              <- the FastAPI service (a Python package)
    ├── __init__.py
    ├── config.py  bilingual.py  orchestrator.py  chatstore.py  catalog.py  server.py
    └── tools\  (search_cases, query_graph, get_statistics, explain_term, display_chart)
```

All backend code lives under `backend\` as a proper Python package (internal
imports are package-relative, e.g. `from . import config`). It must be run
**from the project root** (the parent of `backend\`), not from inside
`backend\` itself — that's what makes `backend.server` resolvable and keeps
`accidents.db` / `chats.db` / `lancedb\` resolving correctly, since those
data files stay at the project root, not inside `backend\`.

The React frontend is located in `frontend\`. During development, run it with
Vite on port 3000. A production frontend build is served directly by FastAPI
from `frontend\dist\`.

## Run the backend (from the project root, Neo4j Desktop DBMS started, venv active)
```powershell
pip install -r requirements.txt
uvicorn backend.server:app --reload --port 8000
```
Exercise it directly at `http://localhost:8000/docs` (FastAPI's interactive
API explorer) until a frontend is wired back up. `server.py` auto-mounts a
`frontend\dist\` folder (at the project root, next to `backend\`) if one
exists, so dropping in a new built frontend and restarting is all that's
needed once the new design is ready.

## What each file does
- backend\config.py       env + lazy clients (OpenAI, LanceDB, Neo4j, read-only SQLite)
- backend\bilingual.py    Hangul-ratio language detection + glossary-aware EN->KO translation
- backend\chatstore.py    SQLite-backed conversation/message persistence (`chats.db`)
- backend\tools\          one module per store; each exports SCHEMA (OpenAI tool def) + run()
- backend\orchestrator.py GPT-4o streaming tool-calling loop (max 6 rounds), yields UI events
- backend\server.py       FastAPI: conversation CRUD, `/api/chat` SSE stream, `/api/cases`,
                          `/api/graph`; mounts `frontend\dist\` when a production build exists

Note: `eval\run_eval.py` and `eval\agent_metrics.py` import from `backend\`
too (`from backend import orchestrator` / `config`) — also run those from
the project root.

## Safety rails built in
- SQL tool: read-only connection + SELECT-only validation
- Cypher tool: write-keyword blocklist (MERGE/DELETE/SET/... rejected)
- Tool results truncated (50 rows / 8000 chars) to keep context bounded
