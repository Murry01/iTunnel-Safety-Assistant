"""RQ1/RQ4 bookkeeping; citation validity is not claim-level faithfulness."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import config
from eval.support import ROOT, completed, digest, latest_records, load_records, now, write_json

CASE_RE = re.compile(r"\bTA-\d{4}\b")


def valid_case_ids():
    con = config.sqlite_conn_readonly()
    try:
        return {r[0] for r in con.execute("SELECT case_id FROM accidents")}
    finally:
        con.close()


def routing_score(record):
    """Binary satisfaction of required/alternative tools. Extra calls reported separately."""
    called = set(record["tools_called"])
    expected = record["expected"]
    required, alternatives = set(expected.get("all_of", [])), set(expected.get("any_of", []))
    return int(required.issubset(called) and (not alternatives or bool(alternatives & called)))


def citation_scores(record, db_ids):
    cited = set(CASE_RE.findall(record.get("answer", "")))
    if not cited:
        return None, 0
    evidence = set(CASE_RE.findall(" ".join(record.get("contexts", []))))
    return len(cited & db_ids & evidence) / len(cited), len(cited)


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def score_record(record, db_ids):
    ok = completed(record)
    validity, count = citation_scores(record, db_ids) if ok else (None, 0)
    required = record.get("citation_required")
    inferred = required is None
    if inferred:
        required = "search_cases" in record["expected"].get("all_of", [])
    allowed = set(record["expected"].get("all_of", []) + record["expected"].get("any_of", []))
    return {"id": record["id"], "lang": record["lang"], "category": record["category"],
            "completed": ok,
            "routing_observed": routing_score(record),
            "routing_on_completed": routing_score(record) if ok else None,
            "completion_and_routing": int(ok and routing_score(record)),
            "additional_tools": sorted(set(record["tools_called"]) - allowed),
            "citation_required": required, "citation_requirement_inferred": inferred,
            "citation_present_when_required": int(count > 0) if ok and required else None,
            "citation_validity": validity, "citation_count": count,
            "tool_error_count": record.get("tool_error_count"),
            "seconds": record.get("seconds"),
            "exact_context_capture": record.get("context_capture") == "exact_model_tool_messages"}


def summarize(rows):
    return {"runs": len(rows), "completed": sum(r["completed"] for r in rows),
            "completion_rate": mean([int(r["completed"]) for r in rows]),
            "routing_accuracy_on_completed": mean([r["routing_on_completed"] for r in rows]),
            "completion_and_routing_rate": mean([r["completion_and_routing"] for r in rows]),
            "citation_presence_when_required": mean([r["citation_present_when_required"] for r in rows]),
            "mean_citation_validity_on_citing_answers": mean([r["citation_validity"] for r in rows]),
            "completed_answers_with_citations": sum(r["citation_count"] > 0 for r in rows),
            "completed_answers_requiring_citations": sum(r["completed"] and r["citation_required"] for r in rows),
            "mean_completed_latency_seconds": mean([r["seconds"] for r in rows if r["completed"]]),
            "legacy_context_records": sum(not r["exact_context_capture"] for r in rows)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=ROOT / "eval/results.json")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    output = args.output or args.input.with_name("metrics_v2.json")
    if output.exists():
        ap.error("Output exists; choose a new --output to preserve previous results.")
    attempts = load_records(args.input)
    records = latest_records(attempts)
    ids = valid_case_ids()
    rows = [score_record(r, ids) for r in records]
    result = {"created_at": now(), "input_sha256": digest(args.input),
              "database_sha256": digest(config.SQLITE_PATH), "attempt_records_in_input": len(attempts),
              "all_languages": summarize(rows),
              "by_language": {lang: summarize([r for r in rows if r["lang"] == lang])
                              for lang in sorted({r["lang"] for r in rows})},
              "by_category": {cat: summarize([r for r in rows if r["category"] == cat])
                              for cat in sorted({r["category"] for r in rows})},
              "notes": ["Completed means a final nonempty answer, not a correct answer.",
                        "Legacy records cannot establish final-answer completion or exact model evidence.",
                        "Routing allows alternatives in the benchmark; it does not establish graph necessity.",
                        "Citation validity checks identifiers, not whether evidence supports a claim.",
                        "Report completion alongside conditional quality; do not hide failed runs."],
              "rows": rows}
    write_json(output, result)
    print(json.dumps(result["by_language"], indent=2))
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
