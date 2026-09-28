# -*- coding: utf-8 -*-
"""
catalog.py — the actual categorical values from accidents.db, injected into
tool descriptions so the LLM can only spell filter values correctly.

Fixes the '추락 vs 떨어짐' class of failure: the model no longer guesses
Korean category names, it copies them from the provided lists.
"""
from . import config

_CACHE = None
COLS = [
    "tunnel_type", "accident_type", "object_l1", "object_l2",
    "work_process", "cause_l1", "cause_l2", "cause_l3",
]


def values() -> dict[str, list[str]]:
    global _CACHE
    if _CACHE is None:
        con = config.sqlite_conn_readonly()
        try:
            _CACHE = {
                c: [
                    r[0]
                    for r in con.execute(
                        f"SELECT DISTINCT {c} FROM accidents ORDER BY 1"
                    )
                    if r[0]
                ]
                for c in COLS
            }
        finally:
            con.close()
    return _CACHE


def catalog_text() -> str:
    """Category columns with their EXACT allowed values, for tool descriptions."""
    try:
        v = values()
    except Exception:
        return "(category value list unavailable — avoid filtering)"
    lines = ["VALID VALUES (use EXACTLY these strings — never invent values):"]
    for col in COLS:
        vals = v[col]
        if col == "object_l2":
            lines.append(
                f"- {col}: {len(vals)} values — do not filter on this column; "
                "use object_l1 instead"
            )
        else:
            lines.append(f"- {col}: {', '.join(vals)}")
    return "\n".join(lines)
