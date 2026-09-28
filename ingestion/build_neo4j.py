# -*- coding: utf-8 -*-
r"""
build_neo4j.py — Module B (causal/taxonomy graph) on Neo4j Aura.

Implements the agreed ontology:
  (:Accident {case_id, fatalities, summary})
  (:TunnelType {name})       (:AccidentType {name})     (:WorkProcess {name})
  (:AccidentObject {path_key, name, level})  L1 -HAS_SUB-> L2
  (:Cause {path_key, name, level})           L1 -HAS_SUB-> L2 -HAS_SUB-> L3

`path_key` contains the complete hierarchy up to that node. This is required
because the same leaf label can occur under more than one parent; identifying a
taxonomy node by `(name, level)` creates false cross-parent paths.

  (a)-[:OCCURRED_IN]->(:TunnelType)
  (a)-[:RESULTED_IN]->(:AccidentType)     # 사고종류 kept whole (e.g. "절단, 베임")
  (a)-[:DURING]->(:WorkProcess)
  (a)-[:INVOLVED]->(:AccidentObject L2)
  (a)-[:CAUSED_BY]->(:Cause L3)

Requires environment variables:
  PowerShell:  $env:NEO4J_URI      = "neo4j+s://xxxx.databases.neo4j.io"
               $env:NEO4J_USER     = "neo4j"
               $env:NEO4J_PASSWORD = "..."

Usage (from the project root):
  # Legacy command retained in README.md, intentionally commented out:
  # python "ingestion\\build_neo4j.py"
  python ingestion\build_neo4j.py --replace
  python ingestion\build_neo4j.py data\Tunnel_data_master.csv --replace
"""
import argparse
import json
import os
import sys

from neo4j import GraphDatabase

try:
    from .common import load_master
except ImportError:  # direct script execution: python ingestion/build_neo4j.py
    from common import load_master

LEGACY_CONSTRAINTS = ["object_key", "cause_key"]

CONSTRAINTS = [
    "CREATE CONSTRAINT accident_id IF NOT EXISTS FOR (a:Accident) REQUIRE a.case_id IS UNIQUE",
    "CREATE CONSTRAINT tunnel_name IF NOT EXISTS FOR (t:TunnelType) REQUIRE t.name IS UNIQUE",
    "CREATE CONSTRAINT atype_name IF NOT EXISTS FOR (t:AccidentType) REQUIRE t.name IS UNIQUE",
    "CREATE CONSTRAINT wproc_name IF NOT EXISTS FOR (w:WorkProcess) REQUIRE w.name IS UNIQUE",
    "CREATE CONSTRAINT object_path_key IF NOT EXISTS FOR (o:AccidentObject) REQUIRE o.path_key IS UNIQUE",
    "CREATE CONSTRAINT cause_path_key IF NOT EXISTS FOR (c:Cause) REQUIRE c.path_key IS UNIQUE",
]

INGEST_CYPHER = """
UNWIND $rows AS row
MERGE (a:Accident {case_id: row.case_id})
  SET a.fatalities = row.fatalities,
      a.summary    = row.specific_cause

MERGE (tt:TunnelType {name: row.tunnel_type})
MERGE (a)-[:OCCURRED_IN]->(tt)

MERGE (at:AccidentType {name: row.accident_type})
MERGE (a)-[:RESULTED_IN]->(at)

MERGE (wp:WorkProcess {name: row.work_process})
MERGE (a)-[:DURING]->(wp)

MERGE (o1:AccidentObject {path_key: row.object_l1_key})
  SET o1.name = row.object_l1, o1.level = 'L1'
MERGE (o2:AccidentObject {path_key: row.object_l2_key})
  SET o2.name = row.object_l2, o2.level = 'L2'
MERGE (o1)-[:HAS_SUB]->(o2)
MERGE (a)-[:INVOLVED]->(o2)

MERGE (c1:Cause {path_key: row.cause_l1_key})
  SET c1.name = row.cause_l1, c1.level = 'L1'
MERGE (c2:Cause {path_key: row.cause_l2_key})
  SET c2.name = row.cause_l2, c2.level = 'L2'
MERGE (c3:Cause {path_key: row.cause_l3_key})
  SET c3.name = row.cause_l3, c3.level = 'L3'
MERGE (c1)-[:HAS_SUB]->(c2)
MERGE (c2)-[:HAS_SUB]->(c3)
MERGE (a)-[:CAUSED_BY]->(c3)
"""

BATCH_SIZE = 50

VERIFY_QUERIES = [
    ("Accident nodes",
     "MATCH (a:Accident) RETURN count(a)"),
    ("AccidentType nodes (expect 10)",
     "MATCH (t:AccidentType) RETURN count(t)"),
    ("TunnelType nodes (expect 4)",
     "MATCH (t:TunnelType) RETURN count(t)"),
    ("Cause nodes (all levels)",
     "MATCH (c:Cause) RETURN count(c)"),
    ("CAUSED_BY edges (expect = accidents)",
     "MATCH ()-[r:CAUSED_BY]->() RETURN count(r)"),
]


def path_key(*parts: str) -> str:
    """Unambiguous, readable taxonomy identity."""
    return json.dumps(parts, ensure_ascii=False, separators=(",", ":"))


def main(src: str, replace: bool = False) -> None:
    if not replace:
        raise SystemExit(
            "[refused] Rebuilding Neo4j deletes the existing target graph. "
            "Rerun with --replace after confirming NEO4J_URI points to the "
            "dedicated research database."
        )
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER", "neo4j")
    pwd = os.getenv("NEO4J_PASSWORD")
    if not uri or not pwd:
        raise SystemExit(
            "[error] NEO4J_URI / NEO4J_PASSWORD not set.\n"
            '  PowerShell:  $env:NEO4J_URI = "neo4j+s://xxxx.databases.neo4j.io"\n'
            '               $env:NEO4J_PASSWORD = "..."'
        )

    df = load_master(src)
    rows = df[
        ["case_id", "tunnel_type", "accident_type", "work_process",
         "object_l1", "object_l2", "cause_l1", "cause_l2", "cause_l3",
         "specific_cause", "fatalities"]
    ].to_dict("records")
    for row in rows:
        row["object_l1_key"] = path_key("L1", row["object_l1"])
        row["object_l2_key"] = path_key("L2", row["object_l1"], row["object_l2"])
        row["cause_l1_key"] = path_key("L1", row["cause_l1"])
        row["cause_l2_key"] = path_key("L2", row["cause_l1"], row["cause_l2"])
        row["cause_l3_key"] = path_key(
            "L3", row["cause_l1"], row["cause_l2"], row["cause_l3"]
        )

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    try:
        driver.verify_connectivity()
        print(f"[neo4j] connected to {uri}")

        with driver.session() as session:
            for name in LEGACY_CONSTRAINTS:
                session.run(f"DROP CONSTRAINT {name} IF EXISTS")
            for c in CONSTRAINTS:
                session.run(c)
            print(f"[neo4j] {len(CONSTRAINTS)} constraints ensured")

            # wipe previous accident graph (idempotent rebuild)
            session.run("MATCH (n) DETACH DELETE n")
            print("[neo4j] cleared existing graph")

            for i in range(0, len(rows), BATCH_SIZE):
                batch = rows[i : i + BATCH_SIZE]
                session.run(INGEST_CYPHER, rows=batch)
                print(f"  ingested {min(i + BATCH_SIZE, len(rows))}/{len(rows)}")

            print("[verify]")
            for label, q in VERIFY_QUERIES:
                val = session.run(q).single()[0]
                print(f"  {label}: {val}")

            print("[sample] top accident types:")
            result = session.run(
                "MATCH (a:Accident)-[:RESULTED_IN]->(t:AccidentType) "
                "RETURN t.name AS type, count(a) AS cases "
                "ORDER BY cases DESC LIMIT 5"
            )
            for r in result:
                print(f"  {r['type']}: {r['cases']}")
        print("[done]")
    finally:
        driver.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", nargs="?", default="data/Tunnel_data_master.csv")
    parser.add_argument(
        "--replace", action="store_true",
        help="delete and rebuild the configured dedicated Neo4j graph",
    )
    args = parser.parse_args()
    main(args.src, replace=args.replace)
