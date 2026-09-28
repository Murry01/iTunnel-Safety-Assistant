# -*- coding: utf-8 -*-
"""tools/query_graph.py — Module B: causal/taxonomy graph (Neo4j)."""
import re

from .. import config

GRAPH_SCHEMA = """
Nodes:
  (:Accident {case_id, fatalities, summary})
  (:TunnelType {name})   -- 4 values: 도로터널, 철도터널, 지하차도, 기타
  (:AccidentType {name}) -- 10 values incl. '절단, 베임' (one node, comma inside)
  (:WorkProcess {name})
  (:AccidentObject {path_key, name, level}) -- path-specific taxonomy identity
  (:Cause {path_key, name, level})          -- path-specific taxonomy identity
Relationships:
  (Accident)-[:OCCURRED_IN]->(TunnelType)
  (Accident)-[:RESULTED_IN]->(AccidentType)
  (Accident)-[:DURING]->(WorkProcess)
  (Accident)-[:INVOLVED]->(AccidentObject {level:'L2'})
  (Accident)-[:CAUSED_BY]->(Cause {level:'L3'})
  (AccidentObject L1)-[:HAS_SUB]->(AccidentObject L2)
  (Cause L1)-[:HAS_SUB]->(Cause L2)-[:HAS_SUB]->(Cause L3)
All category names are Korean. Accidents link only to leaf levels;
reach parent categories via HAS_SUB.

CRITICAL RULES:
1. CAUSED_BY only reaches L3 Cause nodes. To query by an L1/L2 cause
   (e.g. 안전수칙 미준수 is L2), you MUST traverse HAS_SUB down to L3 first.
2. Always include the level property when matching Cause or AccidentObject
   by name. A name can exist at different levels or under different parents;
   when a specific hierarchy is intended, match/traverse its parent too.
3. Cause levels: L1 = 설계오류/시공오류; L2 examples: 안전수칙 미준수,
   시공불량, 기계장비관리 미흡; L3 examples: 작업자 부주의, 작업자 통제 미흡.

EXAMPLE — work processes linked to the L2 cause 안전수칙 미준수:
MATCH (c2:Cause {name:'안전수칙 미준수', level:'L2'})-[:HAS_SUB]->(:Cause {level:'L3'})<-[:CAUSED_BY]-(a:Accident)-[:DURING]->(w:WorkProcess)
RETURN w.name AS work_process, count(a) AS cases ORDER BY cases DESC

EXAMPLE — full cause path of fatal accidents:
MATCH (a:Accident)-[:CAUSED_BY]->(c3:Cause {level:'L3'})<-[:HAS_SUB]-(c2:Cause)<-[:HAS_SUB]-(c1:Cause)
WHERE a.fatalities > 0
RETURN a.case_id, c1.name, c2.name, c3.name
"""

SCHEMA = {
    "type": "function",
    "function": {
        "name": "query_graph",
        "description": (
            "Run a read-only Cypher query on the accident causal graph. Use for: "
            "enumerating categories (guaranteed complete lists), cause-chain "
            "patterns, multi-hop questions (e.g. which work processes lead to a "
            "given cause), and counts grouped by graph structure.\n"
            "Graph schema:\n" + GRAPH_SCHEMA
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "cypher": {"type": "string", "description": "read-only Cypher query"},
            },
            "required": ["cypher"],
        },
    },
}

_FORBIDDEN = re.compile(
    r"\b(CREATE|DELETE|DETACH|SET|MERGE|REMOVE|DROP|LOAD\s+CSV|CALL\s+db\.|apoc\.)\b",
    re.IGNORECASE,
)


def run(cypher: str) -> list[dict]:
    if _FORBIDDEN.search(cypher):
        return [{"error": "Only read-only Cypher is allowed (MATCH/RETURN)."}]
    driver = config.neo4j_driver()
    with driver.session() as session:
        result = session.run(cypher)
        rows = [dict(r) for r in result][:50]
    if rows:
        return rows
    return [{
        "result": "This query returned 0 rows. That does NOT mean the data "
        "doesn't exist — it usually means the query itself was too narrow or "
        "slightly wrong (a misspelled category name, a missing 'level' "
        "property, wrong relationship direction, or skipping a HAS_SUB hop). "
        "Before telling the user no data exists: re-check the category name "
        "against the VALID VALUES list, re-check Cause/AccidentObject levels, "
        "and retry with a broader or corrected query (e.g. drop one filter, "
        "or start from the AccidentType/WorkProcess side instead). Only "
        "report an absence of data after a retry also returns nothing.",
    }]


def case_subgraph(case_ids: list[str]) -> dict:
    """Star subgraph + cause hierarchy for cited cases (for the UI graph panel)."""
    driver = config.neo4j_driver()
    q = """
    MATCH (a:Accident) WHERE a.case_id IN $ids
    MATCH (a)-[r]->(n)
    OPTIONAL MATCH (p)-[h:HAS_SUB]->(n)
    RETURN a.case_id AS case_id, type(r) AS rel,
           elementId(n) AS target_id, labels(n)[0] AS target_label,
           n.name AS target_name, elementId(p) AS parent_id,
           labels(p)[0] AS parent_label, p.name AS parent_name
    """
    nodes, edges = {}, []
    with driver.session() as session:
        for rec in session.run(q, ids=case_ids):
            aid = rec["case_id"]
            nodes[aid] = ("Accident", aid)
            tname = rec["target_name"] or "?"
            tkey = f"{rec['target_label']}:{rec['target_id']}"
            nodes[tkey] = (rec["target_label"], tname)
            edges.append((aid, tkey, rec["rel"]))
            if rec["parent_name"]:
                pkey = f"{rec['parent_label']}:{rec['parent_id']}"
                nodes[pkey] = (rec["parent_label"], rec["parent_name"])
                edges.append((pkey, tkey, "HAS_SUB"))
    return {"nodes": nodes, "edges": edges}
