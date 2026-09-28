"""RQ2: paired keyword/vector/hybrid retrieval and blinded relevance review."""
import argparse
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import config
from eval.support import ROOT, digest, environment, failure, now, read_json, write_json


def relevance_metrics(ids, judgments, k):
    """Score a ranked list against fully judged pooled qrels.

    ``pool_recall_at_k`` is recall against the union of cases returned by the
    compared methods. It is not corpus-level recall unless the qrels are marked
    exhaustive.
    """
    ranked = list(dict.fromkeys(ids))[:k]
    labels = judgments["labels"]
    if any(labels.get(cid) not in (0, 1) for cid in ranked):
        return {"status": "pending_judgments"}
    gains = [labels[cid] for cid in ranked]
    relevant = sum(gains)
    all_relevant = sum(v == 1 for v in labels.values())
    precision = relevant / k
    pool_recall = relevant / all_relevant if all_relevant else None
    pool_f1 = (2 * precision * pool_recall / (precision + pool_recall)
               if pool_recall is not None and precision + pool_recall else 0.0)
    first_relevant = next((rank for rank, gain in enumerate(gains, start=1) if gain), None)
    dcg = sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains, start=1))
    ideal_relevant = min(all_relevant, k)
    idcg = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_relevant + 1))
    return {"status": "scored", "precision_at_k": precision,
            "hit_at_k": int(relevant > 0),
            "recall_at_k": relevant / all_relevant if judgments.get("exhaustive") and all_relevant else None,
            "pool_recall_at_k": pool_recall,
            "pool_f1_at_k": pool_f1,
            "reciprocal_rank": 1 / first_relevant if first_relevant else 0.0,
            "ndcg_at_k": dcg / idcg if idcg else None,
            "pool_relevant": all_relevant,
            "returned": len(ranked)}


def aggregate_scores(rows):
    """Macro-average completed question-level scores by retrieval method."""
    fields = ["precision_at_k", "hit_at_k", "pool_recall_at_k", "pool_f1_at_k",
              "reciprocal_rank", "ndcg_at_k"]
    methods = sorted({row["method"] for row in rows})
    summary = []
    for method in methods:
        completed = [row for row in rows if row["method"] == method and row.get("status") == "scored"]
        entry = {"method": method, "questions_scored": len(completed)}
        for field in fields:
            values = [row[field] for row in completed if row.get(field) is not None]
            entry[f"macro_{field}"] = sum(values) / len(values) if values else None
        summary.append(entry)
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", type=Path, default=ROOT / "eval/dataset.json")
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--keyword-only", action="store_true", help="Offline smoke check, not full RQ2 comparison")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--judgments", type=Path, help="Score existing results against reviewed relevance labels")
    args = ap.parse_args()
    if args.k < 1:
        ap.error("k must be positive")
    output = args.output_dir
    results_file = output / "retrieval.json"
    if args.judgments:
        saved = read_json(results_file)
        judged = read_json(args.judgments)
        if judged["retrieval_sha256"] != digest(results_file):
            ap.error("Judgments refer to different retrieval results")
        scores = []
        for row in saved["rows"]:
            if row["status"] != "completed":
                scores.append({"id": row["id"], "method": row["method"], "status": "retrieval_error"})
                continue
            item = judged["items"].get(row["id"], {"labels": {}})
            reviewed = bool(item.get("reviewer")) and bool(item.get("reviewed_at"))
            metrics = relevance_metrics(row["case_ids"], item, saved["spec"]["k"]) if reviewed else {"status": "pending_review"}
            scores.append({"id": row["id"], "method": row["method"], **metrics})
        score_path = output / "retrieval_scores.json"
        if score_path.exists():
            ap.error("Scores exist; preserve them before rescoring")
        summary = aggregate_scores(scores)
        write_json(score_path, {"judgments_sha256": digest(args.judgments), "rows": scores,
                                "summary": summary,
                                "recall_scope": "pooled retrieval union; not exhaustive corpus recall"})
        print(json.dumps({"rows": scores, "summary": summary}, indent=2))
        return
    methods = ["keyword"] if args.keyword_only else ["keyword", "vector", "hybrid"]
    tbl = config.lance_table()
    spec = {"dataset_sha256": digest(args.dataset), "runner_sha256": digest(__file__),
            "database_sha256": digest(config.SQLITE_PATH), "environment": environment(),
            "k": args.k, "methods": methods, "embedding_model": config.EMBED_MODEL,
            "lance_version": tbl.version, "lance_rows": tbl.count_rows(),
            "indexes": [str(i) for i in tbl.list_indices()],
            "query_policy": "Original Korean question, no filters; same vector for vector and hybrid",
            "method_order": "fixed keyword/vector/hybrid; latency descriptive only (cache/order effects)"}
    if args.resume:
        saved = read_json(results_file)
        if saved["spec"] != spec:
            ap.error("Configuration changed; use a new output directory")
    else:
        if output.exists():
            ap.error("Output exists; use --resume or a new directory")
        saved = {"created_at": now(), "spec": spec, "rows": [], "embeddings": {}}
        write_json(results_file, saved)
    items = [i for i in read_json(args.dataset)["items"] if i["category"] == "narrative_search"]
    for item in items:
        q = item["question_ko"]
        for method in methods:
            if any(r["id"] == item["id"] and r["method"] == method for r in saved["rows"]):
                continue
            started = time.monotonic()
            row = {"id": item["id"], "question": q, "method": method}
            try:
                if method != "keyword" and item["id"] not in saved["embeddings"]:
                    response = config.openai_client().with_options(timeout=60).embeddings.create(model=config.EMBED_MODEL, input=[q])
                    saved["embeddings"][item["id"]] = {"vector": response.data[0].embedding,
                                                          "usage": response.usage.model_dump()}
                    write_json(results_file, saved)
                if method == "keyword":
                    hits = tbl.search(q, query_type="fts").limit(args.k).to_list()
                elif method == "vector":
                    hits = tbl.search(saved["embeddings"][item["id"]]["vector"], query_type="vector").limit(args.k).to_list()
                else:
                    hits = tbl.search(query_type="hybrid").vector(saved["embeddings"][item["id"]]["vector"]).text(q).limit(args.k).to_list()
                row.update(status="completed", case_ids=[h["case_id"] for h in hits])
            except Exception as exc:
                row.update(status="error", error=failure(exc), case_ids=[])
            row["seconds_including_uncached_embedding"] = round(time.monotonic() - started, 3)
            saved["rows"].append(row)
            write_json(results_file, saved)
            print(f"{item['id']} {method}: {row['status']}, {len(row['case_ids'])} cases", flush=True)
    # Case order hides method/rank from the relevance assessor. Labels remain blank.
    review_path = output / "relevance_review.json"
    if not review_path.exists():
        review = {"retrieval_sha256": digest(results_file), "items": {}}
        con = config.sqlite_conn_readonly()
        try:
            for item in items:
                ids = sorted({cid for row in saved["rows"] if row["id"] == item["id"] for cid in row["case_ids"]})
                cases = []
                for cid in ids:
                    cur = con.execute("SELECT case_id,narrative,post_actions,prevention FROM accidents WHERE case_id=?", (cid,))
                    record = cur.fetchone()
                    cases.append(dict(zip([c[0] for c in cur.description], record)))
                review["items"][item["id"]] = {"question": item["question_ko"], "reviewer": "", "reviewed_at": "",
                                                "exhaustive": False, "labels": {cid: None for cid in ids}, "cases": cases}
        finally:
            con.close()
        write_json(review_path, review)
    print(f"Saved {output}. Relevance judgments are pending; no accuracy is claimed.")


if __name__ == "__main__":
    main()
