# Code Review Disposition - Culvert NoDb Writer Hardening

## Metadata

- **Package**: `docs/work-packages/20260805_culvert_nodb_writer_hardening/`
- **Reviewer**: independent Codex reviewer `batch_runtime_station_review`
- **Review date**: 2026-08-06 UTC
- **Base revision**: `bf88592dddd728df124edeff2ed78283148c2cdc`
- **Scope**: route submission, culvert parent/child/finalizer RQ paths,
  `CulvertsRunner`, focused tests, generated RQ graph artifacts, and package
  documentation.

## Findings and Disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| CR-01 | Medium | A successful retry could retain an earlier `_runs[run_id]["error"]`; the manifest would then show success with the stale failure. | Resolved. The finalizer now removes its prior `status`, `error`, and `validation_metrics` fields before applying current run-local metadata, including removal from the persisted record. A failed-to-successful refinalization regression verifies NoDb state, counts, and manifest output. |
| CR-02 | Low | Generated RQ graph source locations drifted after route code moved. | Resolved. Both generated artifacts were refreshed; `wctl check-rq-graph` passes. |
| CR-03 | Low | Early validation failures did not explicitly prove child shared-write isolation. | Resolved. Outside-watershed and minimum-area paths now run with all `CulvertsRunner.locked()` calls forbidden and assert `_runs` remains empty. |
| CR-04 | Low | Stale retry coverage did not exercise bounded exhaustion. | Resolved. The initial-state regression now covers recovery and persistent stale exhaustion at the configured attempt limit. |
| CR-05 | Low | Active ExecPlan context and interface details were stale. | Resolved. Pre-change context is labeled and the route/task signatures match the code. |

## Re-review Verdict

- **Correctness**: PASS.
- **Remaining High findings**: 0.
- **Remaining Medium findings**: 0.
- **Remaining Low findings**: 0.
- **Release recommendation**: ship after normal deployment controls.

The reviewer confirmed all four requested ownership guarantees, authoritative
retry finalization, unchanged stale-write protection, unchanged route security
contracts, and current RQ graph artifacts.

## Validation Considered

- Focused culvert/rq-engine suite: `43 passed`.
- Full suite after remediation: `5,842 passed`, `61 skipped`.
- `wctl check-rq-graph`: pass.
- Changed-file broad-exception enforcement: pass; four fewer unsuppressed
  broad catches than the base revision.
- `git diff --check`: pass.

## Residual Risk

- Concurrency tests deterministically simulate generation changes rather than
  launching multiple OS processes.
- Planned child receipt persistence remains bounded best effort; finalizer
  reconstruction preserves result completeness if those receipts are absent.
- Manual retry can retain an older shared RQ receipt; the retry API response and
  RQ metadata remain the live identity source.
