"""RQ4: export exact evidence for human claim-level grounding review."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from eval.support import completed, digest, latest_records, load_records, now, write_json


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("Output exists; choose a new filename to preserve annotations")
    items = []
    excluded = []
    for r in latest_records(load_records(args.input)):
        if not completed(r):
            excluded.append({"id": r["id"], "lang": r["lang"], "reason": "not_completed"})
            continue
        items.append({"id": r["id"], "lang": r["lang"], "question": r["question"], "answer": r["answer"],
                      "model_evidence": r["contexts"], "reference": r["reference"],
                      "context_capture": r.get("context_capture", "legacy_truncated"),
                      "reviewer": "", "reviewed_at": "", "claims": [],
                      "numerical_accuracy": None, "cause_chain_accuracy": None, "notes": ""})
    write_json(args.output, {"created_at": now(), "input_sha256": digest(args.input),
                            "instructions": "Split each factual answer into atomic claims. For each add text, label (supported/unsupported/contradicted), evidence_index and evidence_quote. Check numbers and cause chains against the frozen SQL reference tables. Leave unreviewed fields null. Case-ID validity alone does not prove support. Do not label legacy truncated evidence as definitive faithfulness.",
                            "items": items, "excluded": excluded})
    print(f"Saved {len(items)} review items; {len(excluded)} noncompleted runs excluded.")


if __name__ == "__main__":
    main()
