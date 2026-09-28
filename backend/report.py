# -*- coding: utf-8 -*-
"""
report.py — deterministic "Prevention Report" generator.

No LLM calls anywhere in this module. Every number, category, and case_id
in the output comes directly from a SQL or Cypher query against the real
stores. This is a fixed reference document (planning input / incident
comparison reference), not a conversational answer, so it must never
fabricate anything the way an open-ended agent turn theoretically could —
see orchestrator.py for that path instead.

Two output formats, same underlying facts:
  "jha"   — Western Job Hazard Analysis convention: full L1->L2->L3 cause
            hierarchy for the selected work process.
  "krisk" — Korean 위험성평가 convention: causes bucketed into KOSHA's
            4M categories (Man/Machine/Material/Method).

The 4M mapping below was built from the actual distinct Cause/AccidentObject
category values in accidents.db (see catalog.py for the same style of
grounding), not guessed. The taxonomy is inherently Method-heavy — it was
built around "error type" (설계오류/시공오류), not raw hazard type — that's
a property of the source data, not a bug in this mapping.
"""
from . import config

# Cause L2 name -> 4M bucket. Covers all 12 real L2 values (see below).
CAUSE_4M = {
    "안전수칙 미준수": "man",
    "행정조치 미흡": "man",
    "기계장비관리 미흡": "machine",
    "공법선정 미흡": "method",
    "구조검토 미흡": "method",
    "사전조사 미흡": "method",
    "사전검토 미흡": "method",
    "시공계획 미준수": "method",
    "시공불량": "method",
    "안전환경 미제공": "method",  # mixed (material/staffing/info sub-causes) — bucketed as procedural provisioning
    "임의시공": "method",
    "현장계측 미흡": "method",
}

# AccidentObject L1 name -> 4M bucket (a second, independent lens: "what
# was involved" rather than "why it happened"). Object categories outside
# this map (가시설, 시설물, 토사 및 암반, 기타) aren't Machine/Material by
# KOSHA convention and are left out of the 4M breakdown on purpose.
OBJECT_4M = {
    "건설기계": "machine",
    "건설공구": "machine",
    "건설자재": "material",
    "부재": "material",
}

BUCKET_LABELS = {
    "man": "Man (인력)",
    "machine": "Machine (기계)",
    "material": "Material (재료)",
    "method": "Method (방법)",
}


def list_work_processes() -> list[str]:
    con = config.sqlite_conn_readonly()
    try:
        return [r[0] for r in con.execute("SELECT DISTINCT work_process FROM accidents ORDER BY 1")]
    finally:
        con.close()


def _risk_summary(work_process: str, tunnel_type: str | None) -> dict:
    con = config.sqlite_conn_readonly()
    try:
        where = "work_process = ?"
        params = [work_process]
        if tunnel_type:
            where += " AND tunnel_type = ?"
            params.append(tunnel_type)

        total = con.execute(f"SELECT COUNT(*), SUM(fatalities) FROM accidents WHERE {where}", params).fetchone()
        by_type = con.execute(
            f"SELECT accident_type, COUNT(*), SUM(fatalities) FROM accidents WHERE {where} "
            "GROUP BY accident_type ORDER BY 2 DESC",
            params,
        ).fetchall()
    finally:
        con.close()
    return {
        "total_cases": total[0] or 0,
        "total_fatalities": total[1] or 0,
        "by_accident_type": [
            {"accident_type": t, "count": n, "fatalities": f or 0} for t, n, f in by_type
        ],
    }


def _measures(work_process: str, tunnel_type: str | None, fmt: str) -> dict | list:
    con = config.sqlite_conn_readonly()
    try:
        where = "work_process = ?"
        params = [work_process]
        if tunnel_type:
            where += " AND tunnel_type = ?"
            params.append(tunnel_type)
        rows = con.execute(
            f"SELECT case_id, accident_type, cause_l2, fatalities, prevention "
            f"FROM accidents WHERE {where} ORDER BY fatalities DESC, case_id LIMIT 20",
            params,
        ).fetchall()
    finally:
        con.close()

    items = [
        {"case_id": cid, "accident_type": at, "cause_l2": c2, "fatalities": f, "prevention": prev}
        for cid, at, c2, f, prev in rows
    ]
    if fmt != "krisk":
        return items

    buckets: dict[str, list] = {"man": [], "machine": [], "method": [], "material": []}
    for item in items:
        bucket = CAUSE_4M.get(item["cause_l2"], "method")
        buckets[bucket].append(item)
    return buckets


def _cause_hierarchy_jha(work_process: str, tunnel_type: str | None) -> list[dict]:
    driver = config.neo4j_driver()
    where_tt = "MATCH (a)-[:OCCURRED_IN]->(:TunnelType {name:$tt})" if tunnel_type else ""
    q = f"""
    MATCH (a:Accident)-[:DURING]->(:WorkProcess {{name:$wp}})
    {where_tt}
    MATCH (a)-[:CAUSED_BY]->(c3:Cause {{level:'L3'}})<-[:HAS_SUB]-(c2:Cause)<-[:HAS_SUB]-(c1:Cause)
    RETURN c1.name AS l1, c2.name AS l2, c3.name AS l3, count(a) AS n
    ORDER BY n DESC
    """
    params = {"wp": work_process}
    if tunnel_type:
        params["tt"] = tunnel_type
    with driver.session() as session:
        return [dict(r) for r in session.run(q, **params)]


def _cause_hierarchy_krisk(work_process: str, tunnel_type: str | None) -> dict:
    driver = config.neo4j_driver()
    where_tt = "MATCH (a)-[:OCCURRED_IN]->(:TunnelType {name:$tt})" if tunnel_type else ""
    cause_q = f"""
    MATCH (a:Accident)-[:DURING]->(:WorkProcess {{name:$wp}})
    {where_tt}
    MATCH (a)-[:CAUSED_BY]->(:Cause {{level:'L3'}})<-[:HAS_SUB]-(c2:Cause {{level:'L2'}})
    RETURN c2.name AS category, count(a) AS n ORDER BY n DESC
    """
    object_q = f"""
    MATCH (a:Accident)-[:DURING]->(:WorkProcess {{name:$wp}})
    {where_tt}
    MATCH (a)-[:INVOLVED]->(:AccidentObject {{level:'L2'}})<-[:HAS_SUB]-(o1:AccidentObject {{level:'L1'}})
    RETURN o1.name AS category, count(a) AS n ORDER BY n DESC
    """
    params = {"wp": work_process}
    if tunnel_type:
        params["tt"] = tunnel_type

    buckets: dict[str, list] = {"man": [], "machine": [], "material": [], "method": []}
    with driver.session() as session:
        for rec in session.run(cause_q, **params):
            bucket = CAUSE_4M.get(rec["category"], "method")
            buckets[bucket].append({"category": rec["category"], "count": rec["n"], "dimension": "cause"})
        for rec in session.run(object_q, **params):
            bucket = OBJECT_4M.get(rec["category"])
            if bucket:
                buckets[bucket].append({"category": rec["category"], "count": rec["n"], "dimension": "object"})
    return buckets


def build_report(work_process: str, tunnel_type: str | None, fmt: str) -> dict:
    fmt = fmt if fmt in ("jha", "krisk") else "jha"
    report = {
        "work_process": work_process,
        "tunnel_type": tunnel_type,
        "format": fmt,
        "risk_summary": _risk_summary(work_process, tunnel_type),
        "measures": _measures(work_process, tunnel_type, fmt),
        "causes_available": True,
    }
    try:
        if fmt == "jha":
            report["causes"] = _cause_hierarchy_jha(work_process, tunnel_type)
        else:
            report["causes"] = _cause_hierarchy_krisk(work_process, tunnel_type)
    except Exception as e:
        report["causes_available"] = False
        report["causes_error"] = str(e)
        report["causes"] = [] if fmt == "jha" else {"man": [], "machine": [], "material": [], "method": []}
    return report
