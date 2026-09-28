# -*- coding: utf-8 -*-
"""tools/get_statistics.py — Module C: analytical statistics (SQLite)."""
import re

from .. import config

TABLE_SCHEMA = """
Table accidents (310 rows, one per accident):
  case_id TEXT PRIMARY KEY      -- 'TA-0001'..'TA-0310'
  tunnel_type TEXT              -- 터널분류: 도로터널, 철도터널, 지하차도, 기타
  accident_type TEXT            -- 사고종류 (10 values incl. '절단, 베임')
  object_l1 TEXT, object_l2 TEXT  -- 사고객체 대/소분류
  work_process TEXT             -- 작업프로세스 (e.g. 해체작업, 설치작업, 천공작업)
  cause_l1 TEXT, cause_l2 TEXT, cause_l3 TEXT  -- 사고원인 hierarchy
  fatalities INTEGER            -- 사망자 count
  specific_cause, damage, future_plan, narrative, post_actions, prevention TEXT
All categorical values are Korean strings — filter with Korean literals,
e.g. WHERE work_process = '해체작업'.
"""

from .. import catalog
try:
    TABLE_SCHEMA += "\n" + catalog.catalog_text()
except Exception:
    pass

SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_statistics",
        "description": (
            "Run a read-only SQL query (SQLite) over the accidents table. Use for: "
            "counts, rates, rankings, aggregations, and exact lookups by case_id. "
            "This is the ONLY reliable tool for 'how many / which is most / top N' "
            "questions — never estimate counts from search results.\n"
            + TABLE_SCHEMA
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "a single SELECT statement"},
            },
            "required": ["sql"],
        },
    },
}

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|PRAGMA|VACUUM)\b",
    re.IGNORECASE,
)


def run(sql: str) -> list[dict]:
    if _FORBIDDEN.search(sql) or not sql.strip().lower().startswith("select"):
        return [{"error": "Only a single SELECT statement is allowed."}]
    con = config.sqlite_conn_readonly()
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchmany(50)
        return [dict(zip(cols, r)) for r in rows] or [{"result": "no rows"}]
    except Exception as e:  # surface SQL errors to the agent so it can retry
        return [{"error": f"SQL error: {e}"}]
    finally:
        con.close()
