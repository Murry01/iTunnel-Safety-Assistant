"""Resumable, paced agent evaluation. Korean is the primary experiment."""
import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import config, orchestrator
from eval.support import ROOT, completed, digest, environment, failure, load_records, now, read_json, write_json


def run_one(question, agent=None, tools=None):
    agent = agent or orchestrator.run_agent
    tools = tools or orchestrator.TOOLS
    trace, contexts, usage, warnings = [], [], [], []
    terminal = {}
    started = time.monotonic()

    def observe(kind, payload):
        if kind == "evidence":
            trace.append(payload)
            contexts.append(payload["model_content"])
        elif kind == "usage":
            usage.append(payload)
        elif kind == "completion":
            terminal.update(payload)
        else:
            warnings.append({"kind": kind, **payload})

    def execute(name, args):
        try:
            return tools[name].run(**args)
        except Exception as exc:
            if failure(exc)["retryable"]:
                raise
            return [{"error": type(exc).__name__}]

    answer, error = "", None
    try:
        for event in agent(question, observer=observe, tool_executor=execute):
            if event[0] == "delta":
                answer += event[1]
            elif event[0] == "done":
                answer = event[1]
        status = "completed" if terminal.get("reason") == "final_answer" and answer.strip() else "incomplete"
    except Exception as exc:
        error, status = failure(exc), "error"
    return {"answer": answer, "status": status, "error": error,
            "tools_called": [t["tool"] for t in trace], "trace": trace,
            "contexts": contexts, "context_capture": "exact_model_tool_messages",
            "completion": terminal, "usage": usage, "warnings": warnings,
            "tool_error_count": sum(any(isinstance(row, dict) and "error" in row
                                        for row in t["result"]) for t in trace),
            "seconds": round(time.monotonic() - started, 3)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", type=Path, default=ROOT / "eval/dataset.json")
    ap.add_argument("--output-dir", type=Path)
    ap.add_argument("--resume", action="store_true")
    languages = ap.add_mutually_exclusive_group()
    languages.add_argument("--ko-only", action="store_true")
    languages.add_argument("--en-only", action="store_true")
    languages.add_argument("--both", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--delay", type=float, default=30)
    ap.add_argument("--attempts", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=90)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.delay < 0 or args.attempts < 1 or args.timeout <= 0 or (args.limit is not None and args.limit < 1):
        ap.error("delay >= 0, attempts >= 1, timeout > 0, limit >= 1 required")
    items = read_json(args.dataset)["items"]
    if args.limit:
        items = items[:args.limit]
    langs = ["ko", "en"] if args.both else ["en"] if args.en_only else ["ko"]
    spec = {"schema_version": 2, "dataset_sha256": digest(args.dataset),
            "database_sha256": digest(config.SQLITE_PATH),
            "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / "backend").rglob("*.py"))},
            "runner_sha256": digest(__file__), "support_sha256": digest(ROOT / "eval/support.py"),
            "environment": environment(),
            "models": {"agent": config.AGENT_MODEL, "embedding": config.EMBED_MODEL, "translation": config.TRANSLATE_MODEL},
            "temperature": 0.2, "max_tool_rounds": config.MAX_TOOL_ROUNDS,
            "languages": langs, "item_ids": [i["id"] for i in items],
            "delay_seconds": args.delay, "max_attempts": args.attempts,
            "timeout_seconds": args.timeout, "sdk_max_retries": 0,
            "usage_scope": "agent completion requests only; excludes translation and embeddings"}
    if args.dry_run:
        print(json.dumps(spec, ensure_ascii=False, indent=2))
        return
    if args.resume and not args.output_dir:
        ap.error("--resume requires --output-dir")
    out = args.output_dir or ROOT / "eval/runs" / time.strftime("%Y%m%d-%H%M%S")
    manifest, journal = out / "manifest.json", out / "attempts.jsonl"
    if args.resume:
        if not manifest.exists() or read_json(manifest)["spec"] != spec:
            ap.error("Resume refused: manifest missing or dataset/code/configuration changed. Start a new run.")
    else:
        if out.exists():
            ap.error("Output directory exists. Use --resume or a new directory.")
        out.mkdir(parents=True)
        write_json(manifest, {"created_at": now(), "spec": spec})
    records = load_records(journal) if journal.exists() else []
    # Disable SDK defaults only in this evaluation process; one retry layer.
    config._openai = config.openai_client().with_options(max_retries=0, timeout=args.timeout)
    try:
        for item in items:
            for lang in langs:
                previous = [r for r in records if r["id"] == item["id"] and r["lang"] == lang]
                if any(completed(r) for r in previous):
                    continue
                if previous and previous[-1].get("error") and not previous[-1]["error"]["retryable"]:
                    continue
                for attempt in range(len(previous) + 1, args.attempts + 1):
                    wait = args.delay if records else 0
                    prior = previous[-1] if previous else None
                    if prior and (prior.get("error") or {}).get("retryable"):
                        wait = max(wait, prior["error"]["retry_after_seconds"],
                                   min(60, 5 * 2 ** (attempt - 2)) + random.random())
                    if wait:
                        print(f"Waiting {wait:.1f}s before {item['id']}/{lang}...", flush=True)
                        time.sleep(wait)
                    print(f"{item['id']}/{lang} attempt {attempt}/{args.attempts}", flush=True)
                    result = run_one(item[f"question_{lang}"])
                    record = {"id": item["id"], "category": item["category"], "lang": lang,
                              "question": item[f"question_{lang}"], "reference": item["reference"],
                              "expected": item["expected"], "citation_required": item.get("citation_required"),
                              "attempt": attempt, "recorded_at": now(), **result}
                    with journal.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                        handle.flush()
                    records.append(record)
                    previous.append(record)
                    print(f"  {result['status']}, {result['seconds']}s, tool errors={result['tool_error_count']}", flush=True)
                    if result["status"] != "error" or not result["error"]["retryable"]:
                        break
    finally:
        from eval.support import latest_records
        write_json(out / "results.json", latest_records(records))
    print(f"Saved {out}. Failed attempts remain in attempts.jsonl.")


if __name__ == "__main__":
    main()
