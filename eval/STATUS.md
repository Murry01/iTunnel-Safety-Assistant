# Evaluation improvement status

Updated 2026-09-20. Research proof of concept; custom orchestrator retained.

## Implemented and verified

- Exact model tool-message capture, with complete raw tool results retained.
- Completed / incomplete / error classification; model round-limit and truncation
  no longer count as completed answers.
- Paced Korean-primary evaluation, explicit bounded retries, Retry-After handling,
  unique run folders, resumable attempt journals, configuration fingerprints.
- Binary routing scoring, separate completion rate, conditional metrics and
  separate citation presence/validity. Legacy pilot remains preserved.
- Fifteen offline regression tests pass, including retry/checkpoint/resume and
  path-specific taxonomy identity.
- One real API statistics smoke test completed, chose get_statistics, saved
  evidence and usage. This is integration verification, not an accuracy study.
- Keyword baseline executed on the three pilot narrative questions.
- All nine keyword/vector/hybrid searches completed for the three narrative
  questions in `runs/retrieval-v2`. The primary researcher reviewed all 29
  blinded pooled question-case pairs. Scores are saved in
  `runs/retrieval-v2/retrieval_scores.json`.
- On this three-question pilot, hybrid and vector both achieved macro
  Precision@5 = 0.400. Hybrid had the highest pooled recall (0.722), MRR (0.750),
  and nDCG@5 (0.630). Keyword scored 0.267, 0.417, 0.333, and 0.320 respectively.
  These are pilot estimates; pooled recall is not corpus-level recall. A concise
  manuscript-facing interpretation is saved in `runs/retrieval-v2/RESULTS.md`.
- Read-only SQLite/LanceDB validation confirms 310 cases; full graph validation
  code compares case-specific cause paths with SQLite.
- Grounding-review export implemented. RAGAS scorer uses the installed modern
  collections API, excludes inexact/legacy evidence, and supports dry-run/resume.
- RAGAS dependency incompatibility repaired using the optional pinned evaluation
  requirements. Package consistency check passes. The supplementary judge scored
  the single live statistics smoke answer at 1.0 faithfulness; one answer is not
  evidence of general system quality. Saved as `faithfulness-compatible.json`
  within `runs/smoke-v2-network`.

## Current graph finding

- Before correction, read-only validation found all 310 source cause paths plus
  15 false paths (precision 0.953846, recall 1.0). Object paths matched exactly.
- Root cause: L3 label `작업순서 미준수` occurs beneath two L2 parents, while the
  live graph identifies Cause nodes by `(name, level)`.
- Ingestion now assigns full hierarchy `path_key` identities, removes the legacy
  uniqueness constraints during an authorized rebuild, and protects rebuilds
  behind an explicit `--replace` flag.
- The dedicated live graph was rebuilt with user authorization. Post-rebuild
  validation reports exact cause and object paths: precision 1.0, recall 1.0,
  no missing/extra paths and no duplicate path rows. Artifact:
  `store_validation_rebuilt.json`.
- Functional graph queries and the JHA cause report return data after rebuild.
  The ENUM-2 pilot reference was corrected because its old counts included false
  paths from the previous shared L3 node.

## Pending or blocked

- A balanced 40-question candidate benchmark has been generated from the frozen
  database with exact reference rows and reviewer guidance. It contains 8
  statistical, 10 graph, 10 narrative, 8 multi-source, and 4 terminology items.
  It remains a candidate until the domain reviewer approves/revises/excludes the
  questions and a separate final benchmark is frozen.
- Claim-level grounding still requires domain review.
- Full primary agent run, graph-specific question experiments, and supplementary
  judge scores are not final manuscript results yet.

See README.md for commands and metric definitions.
