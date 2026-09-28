# -*- coding: utf-8 -*-
"""tools/search_cases.py — Module A: hybrid semantic search (LanceDB)."""
from .. import catalog, config

try:
    _CATALOG = catalog.catalog_text()
except Exception:
    _CATALOG = "(category values unavailable)"

SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_cases",
        "description": (
            "Find tunnel accident cases similar to a Korean query using hybrid "
            "(vector + keyword) search over accident narratives. Use for: "
            "similar-case lookup, retrieving 사고경위 (what happened), "
            "재발방지대책 (prevention measures), and narrative details. "
            "The query MUST be in Korean — translate English questions first.\n"
            "filter_sql is OPTIONAL and should be used sparingly: prefer NO "
            "filter (semantic search already ranks by relevance); if you do "
            "filter, use at most ONE condition, and copy values exactly from "
            "the lists below. If a filtered search returns nothing, it is "
            "automatically retried without the filter.\n" + _CATALOG
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query_ko": {"type": "string", "description": "Korean search query"},
                "filter_sql": {
                    "type": "string",
                    "description": "optional single predicate, e.g. \"fatalities > 0\"",
                },
                "k": {"type": "integer", "description": "results to return (default 5)"},
            },
            "required": ["query_ko"],
        },
    },
}


def _hybrid(query_ko: str, qvec, filter_sql, k):
    tbl = config.lance_table()
    search = tbl.search(query_type="hybrid").vector(qvec).text(query_ko)
    if filter_sql:
        search = search.where(filter_sql)
    return search.limit(k).to_list()


def run(query_ko: str, filter_sql: str | None = None, k: int = 5) -> list[dict]:
    qvec = (
        config.openai_client()
        .embeddings.create(model=config.EMBED_MODEL, input=[query_ko])
        .data[0]
        .embedding
    )
    note = None
    try:
        hits = _hybrid(query_ko, qvec, filter_sql, k)
    except Exception as e:
        # bad filter syntax/value -> degrade to unfiltered rather than fail
        hits, note = [], f"filter rejected ({e}); retried without filter"
        filter_sql = None
    if not hits and filter_sql:
        hits = _hybrid(query_ko, qvec, None, k)
        note = (
            f"filter [{filter_sql}] matched 0 cases — these are UNFILTERED "
            "results; tell the user if the filtered subset was empty"
        )
    elif note:
        hits = _hybrid(query_ko, qvec, None, k)

    out = [
        {
            "case_id": h["case_id"],
            "tunnel_type": h["tunnel_type"],
            "accident_type": h["accident_type"],
            "work_process": h["work_process"],
            "fatalities": h["fatalities"],
            "text": h["text"][:1200],
        }
        for h in hits
    ]
    if note:
        out.insert(0, {"note": note})
    return out
