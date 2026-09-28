# RQ2 pilot retrieval results

Completed 2026-09-20 using blinded relevance judgments from the primary
researcher. The pool contains 29 unique question-case pairs from three Korean
narrative questions and the union of keyword, vector, and hybrid top-5 results.

## Macro results across three questions

| Method | Precision@5 | Pooled recall@5 | Pooled F1@5 | MRR | nDCG@5 | Hit@5 |
|---|---:|---:|---:|---:|---:|---:|
| Hybrid | 0.400 | 0.722 | 0.505 | 0.750 | 0.630 | 1.000 |
| Vector | 0.400 | 0.694 | 0.496 | 0.556 | 0.583 | 1.000 |
| Keyword | 0.267 | 0.417 | 0.324 | 0.333 | 0.320 | 0.667 |

Hybrid had the strongest overall pooled coverage and ranking quality, while its
mean Precision@5 tied vector retrieval. Results varied by question: keyword was
best on NARR-1, vector and hybrid were strongest on NARR-2, and vector had the
highest Precision@5 on NARR-3. The pilot therefore supports a benefit from
semantic retrieval and hybrid ranking, but does not show that one method wins on
every question.

## Reporting limits

- Only three development/pilot questions were evaluated, so these values are
  descriptive and should not be treated as stable population estimates.
- Pooled recall uses the judged union of the three methods' retrieved cases. It
  is not recall over all 310 cases.
- The original rankings, completed judgments, hashes, per-question metrics, and
  aggregate metrics are retained in this directory.
