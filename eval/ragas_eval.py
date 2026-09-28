"""RQ4 supplementary LLM-judge faithfulness, using installed RAGAS 0.4 collections.

Human review remains necessary. RQ2 retrieval precision uses case judgments,
not RAGAS precision over mixed SQL/graph/tool-message strings.
"""
import argparse
import asyncio
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import config  # loads the project's environment
from eval.support import completed, digest, environment, failure, latest_records, load_records, now, read_json, write_json


def select_records(records):
    usable, excluded = [], []
    for record in latest_records(records):
        reason = None
        if not completed(record):
            reason = "not_completed"
        elif record.get("context_capture") != "exact_model_tool_messages":
            reason = "legacy_or_inexact_evidence"
        elif not record.get("contexts"):
            reason = "no_tool_evidence"
        if reason:
            excluded.append({"id": record["id"], "lang": record["lang"], "reason": reason})
        else:
            usable.append(record)
    return usable, excluded


async def score(args, records, output):
    from openai import AsyncOpenAI
    from ragas.llms import llm_factory
    from ragas.metrics.collections import Faithfulness
    # Sequential samples, SDK retries bounded; errors are retained, not averaged as zero.
    async with AsyncOpenAI(timeout=90, max_retries=2) as client:
        llm = llm_factory(args.judge_model, client=client, temperature=0, max_tokens=4096)
        metric = Faithfulness(llm=llm)
        done = {(r["id"], r["lang"]) for r in output["rows"]}
        for record in records:
            if (record["id"], record["lang"]) in done:
                continue
            if output["rows"]:
                await asyncio.sleep(args.delay)
            row = {"id": record["id"], "lang": record["lang"]}
            try:
                result = await asyncio.wait_for(metric.ascore(
                    user_input=record["question"], response=record["answer"],
                    retrieved_contexts=record["contexts"]), timeout=240)
                value = float(result.value)
                row.update(status="scored" if math.isfinite(value) else "undefined",
                           faithfulness=value if math.isfinite(value) else None)
            except Exception as exc:
                row.update(status="error", faithfulness=None, error=failure(exc))
            output["rows"].append(row)
            write_json(args.output, output)
            print(f"{row['id']}/{row['lang']}: {row['status']}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--judge-model", default="gpt-4o-mini")
    ap.add_argument("--delay", type=float, default=30)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.delay < 0:
        ap.error("delay must be nonnegative")
    records, excluded = select_records(load_records(args.input))
    print(f"Eligible: {len(records)}; excluded: {len(excluded)}")
    if args.dry_run:
        return
    if not records:
        ap.error("No completed records with exact tool evidence; rerun the agent evaluation first")
    spec = {"input_sha256": digest(args.input), "judge_model": args.judge_model,
            "temperature": 0, "max_tokens": 4096, "delay_seconds": args.delay,
            "environment": environment(), "metric": "RAGAS collections Faithfulness",
            "runner_sha256": digest(__file__), "sdk_max_retries": 2,
            "interpretation": "Supplementary automated judgment; not expert validation or citation accuracy"}
    if args.resume:
        output = read_json(args.output)
        if output["spec"] != spec:
            ap.error("Resume configuration mismatch")
    else:
        if args.output.exists():
            ap.error("Output exists; use --resume or another filename")
        output = {"created_at": now(), "spec": spec, "rows": [], "excluded": excluded}
        write_json(args.output, output)
    asyncio.run(score(args, records, output))


if __name__ == "__main__":
    main()
