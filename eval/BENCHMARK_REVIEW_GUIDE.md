# Guide for reviewing and using the 40-question benchmark

## Purpose

This candidate benchmark evaluates the four research questions for the
proof-of-concept system:

1. **RQ1 — Source selection:** Does the agent select the appropriate tool or
   combination of tools?
2. **RQ2 — Retrieval relevance:** Does case retrieval return relevant accident
   records?
3. **RQ3 — Graph reasoning:** Does the graph support complete and correct
   cause-chain and taxonomy answers?
4. **RQ4 — Grounding:** Are factual claims supported by the evidence returned
   by the tools?

The 40 Korean questions are new candidate evaluation items. English text is a
reviewer gloss only; Korean remains the evaluated input. Do not use these items
for prompt tuning after the benchmark is frozen.

## Benchmark composition

| Question type | Count | Primary expected source |
|---|---:|---|
| Statistical and aggregation | 8 | SQLite through `get_statistics` |
| Graph cause-chain and taxonomy | 10 | Neo4j through `query_graph` |
| Narrative case retrieval | 10 | LanceDB through `search_cases` |
| Multi-source questions | 8 | Graph/SQLite plus case retrieval |
| Terminology | 4 | Glossary through `explain_term` |
| **Total** | **40** | |

## Step 1: review the candidate questions

Use the **Questions** sheet in `benchmark_review_40.xlsx`.

For every row:

1. Read the Korean question and English reviewer gloss.
2. Check that the question is clear, answerable from the project data, and
   relevant to tunnel-construction accident prevention.
3. Select **Approve**, **Revise**, or **Exclude**.
4. If revising, enter the final Korean wording in the revision column. The
   Korean wording is the input used in the experiment.
5. Record why a question was revised or excluded.

Aim to retain at least 30 questions and preserve representation from every
category. Do not change a question merely because one retrieval method appears
to perform poorly.

## Step 2: verify references before freezing

The **References** sheet contains database-derived reference rows and the query
used to produce them.

- Statistical and graph references are exact snapshots of `accidents.db`.
- Narrative reference IDs are relevance seeds. Unless marked
  `structured_complete`, they are not exhaustive relevance judgments.
- Multi-source questions combine an exact numerical or graph component with a
  human review of cited cases and prevention measures.
- Check category terms, counts, graph paths, and ambiguous wording before
  approving the benchmark.

After review, convert the approved rows into a new frozen file such as
`eval/benchmark_final.json`. Record its SHA-256 hash, database hash, model IDs,
retrieval settings, date, and evaluator role. Preserve this candidate file.

## Step 3: run the final evaluation

Run each approved Korean question under the same configuration. Use a fresh
conversation state for each question so earlier answers do not affect later
tool selection. Preserve:

- the exact question;
- selected tools and tool arguments;
- complete tool outputs sent to the model;
- final answer;
- model and embedding-model identifiers;
- token usage, completion status, errors, and elapsed time.

For the primary proof-of-concept result, run every approved question once. If
time and API budget permit, add two repeat runs per question and report both the
first-run result and variability. Never silently replace failed runs.

The project runner should be used after the approved questions are converted to
the frozen benchmark. This avoids manual copying errors and automatically saves
the evidence needed for routing and grounding evaluation.

## Step 4: score RQ1 — source selection

For each completed answer:

- **Routing correct = 1** when all required tools were used.
- **Routing correct = 0** when a required tool was omitted or an unsuitable
  source was used as the basis for the answer.
- Record unnecessary extra tools separately rather than automatically treating
  them as failure.

Report completion rate, routing accuracy among completed answers, and the joint
completion-and-routing rate. Break results down by question category and tool.

## Step 5: score RQ2 — retrieval relevance

Pool unique top-5 cases returned by keyword, vector, and hybrid retrieval.
Remove method names and ranks before human review. For every question-case pair:

- `1` = the case directly addresses the requested situation and requested
  action or prevention information;
- `0` = the case does not directly address the question.

Report Precision@5, MRR, nDCG@5, and pooled recall/F1. Call recall **pooled
recall** unless all relevant cases among all 310 records have been judged.

## Step 6: score RQ3 — graph answers

Compare returned case IDs, category nodes, and full L1-L2-L3 paths with the
reference rows. Calculate set precision, set recall, and exact-match rate.
Preserve path identity: an L3 name occurring under two L2 parents represents two
different graph paths.

## Step 7: score RQ4 — grounding

Split each answer into atomic factual claims. Label each claim:

- **Supported** — directly supported by recorded tool evidence;
- **Unsupported** — not established by the evidence;
- **Contradicted** — conflicts with the evidence.

Record the evidence index or case ID for supported claims. Report supported
claim proportion, unsupported claim proportion, answer-level fully grounded
rate, citation presence, and citation validity. Do not score failed or incomplete
answers as though they were completed answers.

## Interpretation limits

This remains a proof-of-concept benchmark from one 310-case database. Report the
number of questions and evaluators with every result. A single reviewer provides
usable pilot evidence, but a second independent reviewer and agreement statistic
would strengthen publication claims. Do not present tool selection, retrieval
quality, graph correctness, and grounding as one combined accuracy value.
