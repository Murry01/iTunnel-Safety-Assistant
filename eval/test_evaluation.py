"""Offline regression tests; no live model calls or database writes."""
import json
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

from backend import orchestrator
from eval.agent_metrics import citation_scores, routing_score, score_record
from eval.run_eval import run_one
from eval.support import ROOT, failure, latest_records
from eval.retrieval_eval import relevance_metrics
from eval.ragas_eval import select_records
from eval import run_eval
from ingestion.build_neo4j import path_key


class EvaluationTests(unittest.TestCase):
    def record(self, **overrides):
        return {"id": "NARR-1", "lang": "ko", "category": "narrative_search",
                "answer": "Answer", "tools_called": [], "contexts": [],
                "expected": {"all_of": ["search_cases"], "any_of": []}, **overrides}

    def test_missing_tool_gets_zero(self):
        self.assertEqual(routing_score(self.record()), 0)
        self.assertEqual(routing_score(self.record(tools_called=["search_cases"])), 1)

    def test_taxonomy_identity_includes_parent_path(self):
        first = path_key("L3", "시공오류", "안전수칙 미준수", "작업순서 미준수")
        second = path_key("L3", "시공오류", "시공계획 미준수", "작업순서 미준수")
        self.assertNotEqual(first, second)

    def test_composite_requires_both_conditions(self):
        r = self.record(tools_called=["search_cases"], expected={"all_of": ["search_cases"], "any_of": ["query_graph", "get_statistics"]})
        self.assertEqual(routing_score(r), 0)
        r["tools_called"].append("query_graph")
        self.assertEqual(routing_score(r), 1)

    def test_missing_citation_not_perfect(self):
        r = self.record()
        self.assertEqual(citation_scores(r, set()), (None, 0))
        self.assertEqual(score_record(r, set())["citation_present_when_required"], 0)

    def test_citation_must_exist_and_be_retrieved(self):
        r = self.record(answer="TA-0001 TA-0002 TA-9999 TA-0001", contexts=["TA-0001 TA-9999"])
        self.assertEqual(citation_scores(r, {"TA-0001", "TA-0002"}), (1 / 3, 3))

    def test_failure_excluded_from_conditional_quality(self):
        r = score_record(self.record(answer="[AGENT ERROR] 429"), set())
        self.assertFalse(r["completed"])
        self.assertIsNone(r["routing_on_completed"])
        self.assertIsNone(r["citation_present_when_required"])
        self.assertEqual(r["completion_and_routing"], 0)

    def test_retry_classification_and_header(self):
        exc = RuntimeError("secret text should not be persisted")
        exc.status_code = 429
        exc.response = NS(headers={"retry-after": "120"})
        info = failure(exc)
        self.assertTrue(info["retryable"])
        self.assertEqual(info["retry_after_seconds"], 120)
        self.assertNotIn("secret", str(info))
        exc.code = "insufficient_quota"
        self.assertFalse(failure(exc)["retryable"])

    def test_latest_attempt_not_double_counted(self):
        records = [self.record(attempt=1), self.record(attempt=2)]
        self.assertEqual(len(latest_records(records)), 1)
        self.assertEqual(latest_records(records)[0]["attempt"], 2)

    def test_partial_answer_is_incomplete(self):
        def agent(question, observer, tool_executor):
            observer("completion", {"reason": "round_limit"})
            yield ("done", "Partial")
        self.assertEqual(run_one("q", agent=agent)["status"], "incomplete")

    def test_retrieval_waits_for_judgments(self):
        self.assertEqual(relevance_metrics(["TA-0001"], {"labels": {}}, 5)["status"], "pending_judgments")
        result = relevance_metrics(["TA-0001"], {"labels": {"TA-0001": 1}, "exhaustive": False}, 5)
        self.assertEqual(result["precision_at_k"], 0.2)
        self.assertIsNone(result["recall_at_k"])
        self.assertEqual(result["pool_recall_at_k"], 1.0)
        self.assertAlmostEqual(result["pool_f1_at_k"], 1 / 3)
        self.assertEqual(result["reciprocal_rank"], 1.0)
        self.assertEqual(result["ndcg_at_k"], 1.0)

    def test_retrieval_rank_metrics_preserve_order(self):
        judgments = {"labels": {"TA-0001": 0, "TA-0002": 1, "TA-0003": 1}, "exhaustive": False}
        result = relevance_metrics(["TA-0001", "TA-0002"], judgments, 2)
        self.assertEqual(result["precision_at_k"], 0.5)
        self.assertEqual(result["pool_recall_at_k"], 0.5)
        self.assertEqual(result["pool_f1_at_k"], 0.5)
        self.assertEqual(result["reciprocal_rank"], 0.5)
        self.assertLess(result["ndcg_at_k"], 1.0)

    def test_candidate_benchmark_is_complete_and_tool_scoped(self):
        candidate = json.loads((ROOT / "eval/benchmark_candidate_40.json").read_text(encoding="utf-8"))
        questions = candidate["questions"]
        self.assertEqual(len(questions), 40)
        self.assertEqual(len({question["id"] for question in questions}), 40)
        valid_tools = {"get_statistics", "query_graph", "search_cases", "explain_term"}
        self.assertTrue(all(question["reference_rows"] for question in questions))
        self.assertTrue(all(set(question["expected_tools"]) <= valid_tools for question in questions))

    def test_judge_rejects_legacy_evidence(self):
        usable, excluded = select_records([self.record(contexts=["old truncated context"])])
        self.assertEqual(usable, [])
        self.assertEqual(excluded[0]["reason"], "legacy_or_inexact_evidence")

    def test_runner_retries_checkpoints_and_resumes_without_repeating(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            argv = ["run_eval", "--limit", "1", "--attempts", "2", "--delay", "0", "--output-dir", str(out)]
            failed = {"status": "error", "error": {"retryable": True, "retry_after_seconds": 12},
                      "answer": "", "seconds": 1, "tool_error_count": 0}
            success = {"status": "completed", "error": None, "answer": "ok", "seconds": 1, "tool_error_count": 0}
            client = NS(with_options=lambda **kw: NS())
            with patch.object(run_eval.config, "_openai", None), patch.object(run_eval.config, "openai_client", return_value=client), patch.object(run_eval, "run_one", side_effect=[failed, success]) as run, patch.object(run_eval.time, "sleep") as sleep, contextlib.redirect_stdout(io.StringIO()):
                with patch("sys.argv", argv):
                    run_eval.main()
                with patch("sys.argv", argv + ["--resume"]):
                    run_eval.main()
                self.assertEqual(run.call_count, 2)
                self.assertGreaterEqual(sleep.call_args.args[0], 12)
            self.assertEqual(len((out / "attempts.jsonl").read_text(encoding="utf-8").splitlines()), 2)
            self.assertEqual(json.loads((out / "results.json").read_text(encoding="utf-8"))[0]["status"], "completed")

    def test_real_loop_records_exact_model_context(self):
        evidence = [{"text": "x" * 5000 + " TA-0001 " + "y" * 5000}]
        call = NS(index=0, id="call_1", function=NS(name="search_cases", arguments='{"query_ko":"test"}'))
        first = NS(choices=[NS(delta=NS(tool_calls=[call], content=None))])
        second = NS(choices=[NS(delta=NS(tool_calls=None, content="Answer TA-0001"), finish_reason="stop")])
        sent = []

        def create(**kwargs):
            sent.append(json.loads(json.dumps(kwargs["messages"])))
            return iter([first] if len(sent) == 1 else [second])

        client = NS(chat=NS(completions=NS(create=create)))
        with patch.object(orchestrator.config, "openai_client", return_value=client), patch.object(orchestrator.bilingual, "detect_language", return_value="ko"):
            result = run_one("q", tools={"search_cases": NS(run=lambda **kw: evidence)})
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["contexts"][0], sent[1][-1]["content"])
        self.assertEqual(len(result["contexts"][0]), 8000)
        self.assertIn("TA-0001", result["contexts"][0])


if __name__ == "__main__":
    unittest.main()
