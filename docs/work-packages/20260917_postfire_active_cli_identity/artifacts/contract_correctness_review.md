# Independent contract correctness review

2026-09-17. Reviewer: `active_cli_correctness`. Verdict: **PASS for the
contract checkpoint**. Implementation and runtime acceptance remain pending.
No blocking contract finding. No production files edited by this review.

## Scope and rationale

Reviewed the package, active ExecPlan, contract decision, and the active CLI
hard-link amendment in `docs/schemas/file-dependency-freshness-contract.md`
against `production.py`, `run_preparation.py`, `production_soils.py`, the
descriptor-bound digest implementation, and the existing native M3 tests.

The exception is sufficiently narrow: only the active CLI's ctime may differ;
path, size, mtime, selections, other dependencies, and available hash maps
remain exact. An admission-time digest must already exist. A new uncached,
coherent, no-follow read proves unchanged bytes. Legacy hashless attempts keep
strict comparison. This repairs the reported valid workflow without silently
accepting changed climate data or weakening artifact/SQLite guards.

## Required implementation coverage

| Stage | Existing guard | Required change |
| --- | --- | --- |
| M1 and M3 worker admission | Full attempt snapshot equality in `execute_model` / `execute_m3` | Compare input snapshots with the narrow exception; retain exact outer attempt fields and the admitted snapshot as authority. |
| M1 Kf preparation | `_current_authority` after acquisition | Apply the same input comparison; keep `check_attempt` strict. |
| M3 source acquisition and promotion | `prepare_for_run.verify` calls `_current_authority` | Same input comparison before and during source promotion; owner/model/frequency checks stay strict. |
| M3 preparation rebase | `_project_inputs` comparison in `prepare_for_run.rebase` | Apply the exception after excluding only existing owned preparation assets; reject every unrelated input change. |
| Both models before publication | `_current_authority` after model execution | Same exception with a fresh verification of the changed CLI. |
| Both models under publication lock | `_current_authority` inside `publish` | Same exception; preserve result/predictor artifact stat guards and attempt identity. |

Do not replace the admitted snapshot with the latest sampled snapshot merely
to erase ctime drift: M1 and preparation `check_attempt` explicitly compare the
durable attempt against that authority. Only the existing verified M3 source
preparation transaction may rebase its owned source fields. Upload guards use
`rainfall=False`, so have no active CLI and need no exception.

## Evidence required before final approval

- Real hard-link creation and removal at admission, preparation, pre-publication
  and locked publication, including prepared and initially absent M3 sources.
- M1 coverage proving its shared helper integration does not fail the stricter
  dNBR/attempt guard after permitted admission drift.
- Changed CLI bytes with equal size and restored mtime remain rejected;
  source selection, other-input ctime drift, symlink/path replacement,
  absent/malformed hashes and an unstable verification read fail closed.
- Existing accepted result survives failed replacement. Earlier attempt
  evidence remains browsable. A fresh accepted assessment is current.
- Restarted-worker end-to-end overlap with ordinary WEPP materialization and
  actual M3 execution, plus recovery of the named run through normal Run flow.

Residual boundary: mutation during the coherent digest read may still fail
explicitly. The amendment permits ordinary link churn outside that short
verification window; it does not promise arbitrary concurrent-writer snapshot
isolation. This is explicit in the contract and is not a reason to weaken the
descriptor/path generation checks. Final approval requires the real overlap
evidence rather than helper-only tests.
