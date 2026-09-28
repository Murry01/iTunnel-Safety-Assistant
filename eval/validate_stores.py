"""Read-only source/store consistency checks for RQ3 and reference preparation."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import config
from eval.support import ROOT, digest, now, write_json


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--graph", action="store_true", help="Also contact configured Neo4j, read-only")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("Output exists; choose another filename.")
    con = config.sqlite_conn_readonly()
    try:
        rows = con.execute("SELECT case_id,cause_l1,cause_l2,cause_l3,object_l1,object_l2 FROM accidents").fetchall()
        cause_rows = [tuple(row[:4]) for row in rows]
        object_rows = [(row[0], row[4], row[5]) for row in rows]
        report = {"created_at": now(), "database_sha256": digest(config.SQLITE_PATH),
                  "sqlite_integrity": con.execute("PRAGMA quick_check").fetchone()[0],
                  "case_count": len(rows),
                  "reference_tables": {
                      "tunnel_counts_and_deaths": con.execute("SELECT tunnel_type,COUNT(*),SUM(fatalities),SUM(fatalities>0) FROM accidents GROUP BY tunnel_type").fetchall(),
                      "accident_counts_and_deaths": con.execute("SELECT accident_type,COUNT(*),SUM(fatalities) FROM accidents GROUP BY accident_type ORDER BY SUM(fatalities) DESC").fetchall(),
                      "work_process_counts": con.execute("SELECT work_process,COUNT(*) FROM accidents GROUP BY work_process").fetchall(),
                      "cause_paths": con.execute("SELECT cause_l1,cause_l2,cause_l3,COUNT(*) FROM accidents GROUP BY cause_l1,cause_l2,cause_l3").fetchall()},
                  "cause_l3_with_multiple_parent_paths": con.execute("SELECT cause_l3,COUNT(*) FROM (SELECT DISTINCT cause_l1,cause_l2,cause_l3 FROM accidents) GROUP BY cause_l3 HAVING COUNT(*)>1").fetchall(),
                  "object_l2_with_multiple_parent_paths": con.execute("SELECT object_l2,COUNT(*) FROM (SELECT DISTINCT object_l1,object_l2 FROM accidents) GROUP BY object_l2 HAVING COUNT(*)>1").fetchall()}
    finally:
        con.close()
    expected = set(cause_rows)
    expected_objects = set(object_rows)
    from backend.config import lance_table
    tbl = lance_table()
    lance_ids = set(tbl.to_arrow().column("case_id").to_pylist())
    sql_ids = {row[0] for row in rows}
    report["lancedb"] = {"rows": tbl.count_rows(), "version": tbl.version,
                         "missing_case_ids": sorted(sql_ids - lance_ids),
                         "extra_case_ids": sorted(lance_ids - sql_ids),
                         "indexes": [str(i) for i in tbl.list_indices()]}
    report["graph"] = {"status": "not_checked"}
    if args.graph:
        from neo4j import GraphDatabase, Query, READ_ACCESS
        try:
            with GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
                                      connection_timeout=5, connection_acquisition_timeout=10) as driver:
                driver.verify_connectivity()
                with driver.session(default_access_mode=READ_ACCESS) as session:
                    def query(text):
                        return [dict(r) for r in session.run(Query(text, timeout=15))]
                    actual_rows = query("MATCH (a:Accident)-[:CAUSED_BY]->(c3:Cause {level:'L3'})<-[:HAS_SUB]-(c2:Cause {level:'L2'})<-[:HAS_SUB]-(c1:Cause {level:'L1'}) RETURN a.case_id AS case_id,c1.name AS l1,c2.name AS l2,c3.name AS l3")
                    actual = {(r["case_id"], r["l1"], r["l2"], r["l3"]) for r in actual_rows}
                    object_actual_rows = query("MATCH (a:Accident)-[:INVOLVED]->(o2:AccidentObject {level:'L2'})<-[:HAS_SUB]-(o1:AccidentObject {level:'L1'}) RETURN a.case_id AS case_id,o1.name AS l1,o2.name AS l2")
                    actual_objects = {(r["case_id"], r["l1"], r["l2"]) for r in object_actual_rows}
                    report["graph"] = {
                        "status": "checked", "path_exact_match": actual == expected,
                        "path_precision": len(actual & expected) / len(actual) if actual else None,
                        "path_recall": len(actual & expected) / len(expected) if expected else None,
                        "missing_paths": sorted(expected - actual), "extra_paths": sorted(actual - expected),
                        "duplicate_path_rows": len(actual_rows) - len(actual),
                        "object_path_exact_match": actual_objects == expected_objects,
                        "object_path_precision": len(actual_objects & expected_objects) / len(actual_objects) if actual_objects else None,
                        "object_path_recall": len(actual_objects & expected_objects) / len(expected_objects) if expected_objects else None,
                        "missing_object_paths": sorted(expected_objects - actual_objects),
                        "extra_object_paths": sorted(actual_objects - expected_objects),
                        "duplicate_object_path_rows": len(object_actual_rows) - len(actual_objects),
                        "nodes": query("MATCH (n) RETURN labels(n) AS labels,count(*) AS n"),
                        "relationships": query("MATCH ()-[r]->() RETURN type(r) AS relationship,count(*) AS n")}
        except Exception as exc:
            report["graph"] = {"status": "unavailable", "error_type": type(exc).__name__}
    write_json(args.output, report)
    print(json.dumps({"sqlite_integrity": report["sqlite_integrity"], "cases": len(rows),
                      "ambiguous_cause_leaves": len(report["cause_l3_with_multiple_parent_paths"]),
                      "ambiguous_object_leaves": len(report["object_l2_with_multiple_parent_paths"]),
                      "graph": {k: v for k,v in report["graph"].items() if k not in ("missing_paths", "extra_paths", "missing_object_paths", "extra_object_paths", "nodes", "relationships")}}, indent=2))
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
