# Research evaluation: RQ1–RQ4

Run commands from the project root with `.venv` active. The custom orchestrator
is retained. Korean is the primary experiment; English is supplementary.
The 15 existing questions are a **pilot set**, not a held-out final benchmark.

## Current evidence

- `results.json` and `agent_metrics.csv`: preserved July pilot (30 runs, 19 API
  rate-limit exceptions). Do not present these as final manuscript results.
- `metrics_v2_pilot.json`: corrected descriptive scoring of that legacy pilot.
  Legacy evidence is incomplete; no new faithfulness conclusion follows.
- `runs/smoke-v2-network`: one successful live Korean statistics question.
  This verifies integration only, not general accuracy.
- `store_validation_v2_network.json`: SQLite/LanceDB checks and attempted Neo4j
  validation. Neo4j was unreachable; graph correctness is not established.

## 1. Offline verification

```powershell
python -m unittest eval.test_evaluation -v
python eval/run_eval.py --dry-run
python eval/validate_stores.py --output eval/store-check-new.json
python eval/validate_stores.py --graph --output eval/store-check-graph-new.json
```

The last command only reads Neo4j. It does not rebuild or delete graph data.
Graph checks compare every case's cause and object paths against SQLite, including
unexpected extra paths and duplicate path rows. A shared cause name under
multiple parents can create false paths with the current `(name, level)` node
identity. Resolve any mismatch before RQ3 experiments; do not silently rebuild
the graph because the ingestion script clears the target database.

## 2. RQ1: agent routing and execution

```powershell
python eval/run_eval.py --output-dir eval/runs/primary-01
python eval/run_eval.py --output-dir eval/runs/primary-01 --resume
python eval/agent_metrics.py --input eval/runs/primary-01/attempts.jsonl
```

The agent run uses paid model/embedding calls. Defaults: Korean only, 30 seconds
between attempts, three total attempts per question, 90-second request timeout.
Use `--both` only for supplementary bilingual experiments. `--limit 1` provides
a smoke test. Resume with the same flags, code, dataset, and environment.

Each run gets its own directory. A manifest records source/database/dataset
hashes, models, package versions, temperature, and execution limits. Each attempt
is appended to `attempts.jsonl`; the last attempt per question is also exported to
`results.json`. Completed questions are skipped on resume. Permanent errors are
not retried. Temporary API errors use bounded backoff and respect Retry-After.
SDK retries are disabled in this runner to avoid nested API retries. Retries
repeat the entire read-only turn and may incur additional cost. Prior failures
are retained. A forcibly interrupted in-flight attempt may need to be repeated.

The actual model name and token usage returned by completed agent calls are
recorded. This usage **excludes embeddings, translation, and interrupted model
calls**; it is not a total-cost estimate. No prices are assumed.

## Candidate final benchmark

`benchmark_candidate_40.json` contains 40 new Korean-primary questions with
database-derived reference rows. Review them with
`BENCHMARK_REVIEW_GUIDE.md` and the workbook in
`../outputs/benchmark_candidate_40/benchmark_review_40.xlsx`. The candidate set
must be approved and copied to a separately named frozen benchmark before it is
used for final experiments. Rebuild the candidate references, if needed, with:

```powershell
python eval/build_benchmark_candidate.py
```

Routing is binary satisfaction of the benchmark's required tools and acceptable
alternatives. Additional tools are listed, not automatically penalized. Report
completion rate, routing accuracy on completed answers, and completion-and-routing
rate together. Completed does not mean correct; recovered tool errors remain
visible. A round limit, truncated generation, or empty answer is incomplete.

The primary routing policy accepts SQL or graph for several tasks. It cannot
establish that Neo4j is necessary. Distinguish acceptable routing (RQ1) from
the graph-specific factual evaluation (RQ3).

## 3. RQ2: paired retrieval baselines

```powershell
python eval/retrieval_eval.py --output-dir eval/runs/retrieval-01
python eval/retrieval_eval.py --output-dir eval/runs/retrieval-01 --resume
```

Runs keyword-only, vector-only, and hybrid retrieval on the same three Korean
narrative questions, same store, same top-K (default 5), same query text, and no
filters. Each query embedding is generated once and reused. Embeddings, rankings,
index configuration and errors are saved. `--keyword-only` is an offline smoke
check, not the full comparison. Errors remain recorded; resume does not silently
replace them. Use a new directory for another experiment.

`relevance_review.json` pools returned cases in case-ID order without exposing
method or rank in the review file. A domain assessor must fill `reviewer`,
`reviewed_at`, and each label (`1` relevant, `0` irrelevant). Define relevance
before labeling: the case must match the requested incident/situation and contain
information addressing the requested actions or prevention measures. Record any
adjudication separately and preserve original labels.

```powershell
python eval/retrieval_eval.py --output-dir eval/runs/retrieval-01 --judgments eval/runs/retrieval-01/relevance_review.json
```

No accuracy is assigned to unreviewed cases. Precision@K divides by K, including
unfilled result positions. MRR and nDCG@K retain rank information. The scorer
also reports pooled recall and pooled F1 against the union of cases returned by
the compared methods. These pooled metrics support comparison within the frozen
experiment but are not corpus-level recall. `recall_at_k` remains unavailable
unless `exhaustive` is true and **all relevant cases in the corpus have been
assessed and included in the labels**, not just the pooled results. Never mark
pooled labels exhaustive by default. Retrieval timing is descriptive: method
order and cache effects are not controlled for a performance experiment.

## 4. RQ3: graph and numerical correctness

Use the read-only store validator to establish source-to-graph path consistency.
Its reference tables contain counts, deaths, fatal-accident counts, work processes,
and cause paths derived directly from SQLite. Evaluate the agent's answers against
these references separately from checking whether `query_graph` was called.

Before final experiments, add expert-reviewed graph questions with explicit
expected paths/sets. The existing broad narrative references are not exact
ground truth. SQL contains the same cause hierarchy: graph traversal capability
alone does not prove superiority over SQL. Any graph ablation must define which
tools/evidence are available and measure both answer accuracy and completeness.

## 5. RQ4: grounding and human review

```powershell
python eval/grounding_review.py --input eval/runs/primary-01/results.json --output eval/runs/primary-01/grounding_review.json
```

The export includes answers and exact tool messages. For every completed answer,
split factual assertions into atomic claims and label supported, unsupported, or
contradicted. Include the supporting evidence index/quotation and record reviewer
identity. Assess numerical and cause-chain correctness against database references.
Citation-ID validity only checks that the case exists and appears in recorded
evidence; it does not establish that the case supports a claim. Uncited answers
have undefined citation validity, with citation presence reported separately
for questions requiring case evidence. Failed answers are not quality-scored.

Optional supplementary LLM judge (paid calls, RAGAS 0.4 collections API):

```powershell
pip install -r eval/requirements.txt
python eval/ragas_eval.py --input eval/runs/primary-01/results.json --output eval/runs/primary-01/faithfulness.json --dry-run
python eval/ragas_eval.py --input eval/runs/primary-01/results.json --output eval/runs/primary-01/faithfulness.json
```

The optional requirements pin `langchain-community==0.4.1` because installed
RAGAS 0.4.3 imports a module absent from 0.4.2. This is an evaluation dependency;
the application continues to use its custom orchestrator.

The judge model defaults to `gpt-4o-mini`, temperature zero; change it explicitly
with `--judge-model` and report it. Samples run sequentially and save after each
sample. `--resume` skips all previously attempted samples, including errors.
Legacy truncated evidence is excluded. Undefined scores and judge failures remain
explicit. Human assessment is still required. RQ2 case-level precision is measured
using the retrieval baseline, not LLM judgments of mixed SQL/graph message strings.

## Before manuscript results

1. Rebuild the dedicated Neo4j graph with the corrected path-specific taxonomy,
   then require exact cause-path and object-path validation.
2. Review numerical references, routing expectations and citation requirements.
3. Expand and freeze a held-out question set; keep development questions separate.
4. Complete relevance and answer-grounding judgments with a documented rubric.
5. Run the frozen evaluation; retain failures and use repeated runs if studying
   agent variability. Report sample sizes and denominators, not just percentages.
6. Report the configured model IDs, versions, dataset provenance and limitations.

These experiments assess information retrieval and grounded answers, **not a
measured reduction in real construction accidents**. Deaths per recorded accident
are descriptive; without exposure denominators they do not establish which
tunnel type is most dangerous. Bilingual parity is outside the main contribution.

Retry policy reference: https://developers.openai.com/api/docs/guides/rate-limits
