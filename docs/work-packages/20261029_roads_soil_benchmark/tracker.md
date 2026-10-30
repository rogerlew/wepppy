# Roads soil benchmark tracker

Updated: 2026-10-29 21:51 UTC. Study and repository validation complete.

## Completed

- Four generated 7778 specimens and five complete 16-year climates pinned.
- Ten original-duration reference replays and archive deltas retained.
- 96 screening runs and 2,880 matched main runs executed and artifact-validated.
- Held-out Charleston/clay-loam comparisons evaluated without further tuning.
- Fifteen modern native PASS diagnostics and six long-road stress runs retained.
- [Results report](report.md), complete comparisons, figure and provenance written.
- Candidate promotion declined: material out-of-band failures remain. No ADR or
  production contract change is proposed; no full-project integration or deployment.
- Focused benchmark tests: 4 passed. Existing Roads suite: 530 passed, 5 skipped.
- Soil-treatment full-suite shards: all 230 tests passed in disjoint groups.

## Final validation

Full repository coverage across disjoint groups: **12,076 passed, 298 skipped,
no failures**. Disturbed matrix: 99 passed. The focused benchmark tests are
included in the repository total. The original sequential full run was split
for runtime, not because of failures. No required cases were intentionally
omitted. Commands, exact group counts and log hashes are retained in
[validation](artifacts/validation.md).

## Decisions and limitations

Scope/rationale: `package.md`, Objective and accepted scope and Experiment and
acceptance. Final recommendation: `report.md`, Disposition and next bounded
experiment. Scientific decisions and execution deviations are retained in the
completed ExecPlan. Security impact: none for this isolated study.

Reference capture/asset defects, failed attempts and execution source snapshots
remain under `/wc1/runs/ro/roads-soil-benchmark-20261029`. The main report uses
spatial net soil loss and full-profile export, not a mislabeled road-prism or
cross-version PASS metric. Prepared landuse-conditioned soils remain a follow-up.
