# Phase 8 ExecPlan: Forest + Wepp1 Root-Resource Unroll Batch Migration

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current while execution proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Create and execute a batch migration script that walks run and batch project trees on:
- forest: `/wc1/runs` and `/wc1/batch`
- wepp1: `/geodata/wc1/runs` and `/geodata/wc1/batch`

The script must detect in-scope retired WD-root resources and unroll them to canonical directory locations. Forest migration executes first. Wepp1 migration is dry-run only until explicit human approval is recorded; apply on wepp1 must be blocked without that approval.

After completion, eligible `apply_nodir=false` projects on forest (and approved wepp1) have no in-scope WD-root resources remaining, and all migrated resources exist in canonical directory targets.

## Scope Lock

In-scope resources and mapping are locked to:
1. `landuse.parquet` -> `landuse/landuse.parquet`
2. `soils.parquet` -> `soils/soils.parquet`
3. `climate.<name>.parquet` -> `climate/<name>.parquet`
4. `watershed.<name>.parquet` -> `watershed/<name>.parquet`
5. `wepp_cli_pds_mean_metric.csv` -> `climate/wepp_cli_pds_mean_metric.csv`

Migration eligibility and behavior must remain consistent with:
- `docs/work-packages/20260227_nodir_full_reversal/artifacts/phase7_apply_nodir_false_migration_spec.md`
- `docs/work-packages/20260227_nodir_full_reversal/artifacts/phase7_root_resource_inventory.md`

Out of scope:
- `apply_nodir=true` migration
- runtime fallback restoration
- non-locked resources outside the list above

## Progress

- [x] Phase 1 complete: script design and implementation landed with dry-run/apply modes, audit schema, and host gating.
- [x] Phase 2 complete: forest dry-run inventory completed and reviewed.
- [x] Phase 3 complete: forest apply migration completed with post-apply verification.
- [x] Phase 4 complete: wepp1 dry-run inventory completed and approval packet generated (with `460` explicit config-resolution run errors captured for Phase 5 approval disposition).
- [x] Phase 5 complete: explicit human approval recorded for wepp1 apply.
- [x] Phase 6 complete: wepp1 apply migration executed with approved gate artifact, apply audit/summary/report published, and post-apply verification completed.
- [x] Phase 7 complete: closeout artifacts, tracker updates, and final verification publication completed.

## Surprises & Discoveries

- Discovery: forest dry-run found 164 eligible runs and 1024 in-scope root resources, including 2 predicted conflict runs (`ill-taco`, `real-time-preserver`) on `soils.parquet` hash mismatch.
  Impact: forest apply required explicit conflict carry-forward and manual-resolution ledger updates.
  Date/Author: 2026-02-27 / Codex

- Discovery: initial forest apply surfaced transient source-file disappearance in active batch trees; this was hardened to no-op/idempotent skipped behavior for disappearing sources.
  Impact: convergence rerun completed with zero run/file errors and only explicit conflicts remaining.
  Date/Author: 2026-02-27 / Codex

- Discovery: wepp1 roots `/geodata/wc1/runs` and `/geodata/wc1/batch` are not mounted in the execution environment.
  Impact: Phase 4 cannot complete inventory; approval packet published as blocked with concrete root-check evidence.
  Date/Author: 2026-02-27 / Codex

- Discovery: on wepp1, container path mapping is `/wc1 -> /geodata/wc1`; Phase 4 dry-run completed via `wctl exec weppcloud` using `--roots /wc1/runs,/wc1/batch`.
  Impact: Phase 4 moved from blocked to complete with real inventory counts (`6993` discovered runs, `252` eligible, `11` predicted conflicts).
  Date/Author: 2026-02-28 / Codex

- Discovery: wepp1 Phase 6 apply processed `1853` discovered runs and surfaced only explicit non-destructive outcomes (`2` soils hash-conflict runs, `3` config-resolution run errors), with no move/dedup actions executed.
  Impact: wepp1 apply artifacts are complete for operator follow-up; Phase 6 can close while carrying explicit conflict/error ledgers forward.
  Date/Author: 2026-02-28 / Codex

- Discovery: Phase 4 dry-run inventory (`6993` discovered / `252` eligible) and Phase 6 apply inventory (`1853` discovered / `2` eligible) were from different `/wc1` snapshots.
  Impact: a post-apply reconciliation dry-run on the same roots confirmed current-snapshot totals (`1858` discovered / `2` eligible / `2` predicted conflicts / `3` run errors), aligning with Phase 6 apply scope.
  Date/Author: 2026-02-28 / Codex

## Decision Log

- Decision: wepp1 apply requires explicit human approval gate before any file mutation.
  Rationale: user requirement and production-risk isolation.
  Date/Author: 2026-02-27 / Codex

- Decision: run forest first and treat it as canary for script correctness/performance.
  Rationale: faster feedback, lower blast radius than wepp1.
  Date/Author: 2026-02-27 / Codex

- Decision: treat disappearing source files during apply as idempotent no-op (`skipped`) rather than hard error.
  Rationale: active batch trees can mutate between discovery and action; strict errors were non-actionable and prevented clean convergence.
  Date/Author: 2026-02-27 / Codex

- Decision: keep wepp1 Phase 4 as blocked instead of fabricating inventory counts.
  Rationale: contract requires concrete host-root evidence when required roots are inaccessible.
  Date/Author: 2026-02-27 / Codex

- Decision: execute wepp1 dry-run in container context with explicit root override.
  Rationale: wepp1 container maps `/geodata/wc1` to `/wc1`; host defaults are not valid inside container namespace.
  Date/Author: 2026-02-28 / Codex

- Decision: accept explicit human approval artifact with no approval-token requirement.
  Rationale: script only requires token matching when `--approval-token` is provided.
  Date/Author: 2026-02-28 / Codex

- Decision: treat wepp1 apply exit `1` as Phase 6-complete when artifact contract and verification requirements are satisfied.
  Rationale: apply mode is specified to exit non-zero when any run ends `error`; this run produced complete audit/summary/report artifacts with explicit conflict/error disposition.
  Date/Author: 2026-02-28 / Codex

- Decision: use same-root reconciliation dry-run to validate Phase 6 apply scope when prior dry-run inventory is from an older snapshot.
  Rationale: wepp1 run/batch trees are mutable; Phase 6 correctness should be evaluated against the current snapshot that apply actually processed.
  Date/Author: 2026-02-28 / Codex

## Outcomes & Retrospective

- Phase 1 delivered `wepppy/tools/migrations/unroll_root_resources_batch.py` and targeted migration tests.
- Phase 2 delivered forest dry-run artifacts:
  - `artifacts/phase8_forest_dry_run_audit.jsonl`
  - `artifacts/phase8_forest_dry_run_summary.json`
  - `artifacts/phase8_forest_dry_run_report.md`
- Phase 3 delivered forest apply artifacts and post-apply conflict verification:
  - `artifacts/phase8_forest_apply_audit.jsonl`
  - `artifacts/phase8_forest_apply_summary.json`
  - `artifacts/phase8_forest_apply_report.md`
- Phase 4 attempted wepp1 dry-run and produced blocker-backed artifacts:
- Phase 4 completed wepp1 dry-run and approval packet generation using container-root overrides:
  - `artifacts/phase8_wepp1_dry_run_audit.jsonl`
  - `artifacts/phase8_wepp1_dry_run_summary.json`
  - `artifacts/phase8_wepp1_approval_packet.md`
- Phase 5 completed with explicit human approval artifact:
  - `artifacts/phase8_wepp1_approval.md`
- Phase 6 completed with approved wepp1 apply execution + verification artifacts:
  - `artifacts/phase8_wepp1_apply_audit.jsonl`
  - `artifacts/phase8_wepp1_apply_summary.json`
  - `artifacts/phase8_wepp1_apply_report.md`
- Phase 7 completed with final closeout artifacts and status updates:
  - `artifacts/phase8_validation_log.md`
  - `artifacts/phase8_findings_resolution.md`
  - `artifacts/phase8_subagent_review.md`
  - `artifacts/phase8_final_verification.md`
- Residual risk:
  - two explicit forest conflict runs require manual soils parquet resolution;
  - wepp1 apply left two explicit soils conflict runs (`ill-taco`, `real-time-preserver`) and three config-resolution run errors (`ext-disturbed9002.cfg` missing) for manual/operator follow-up.

## Context and Orientation

Phase 7 retired runtime fallback for WD-root resources and established a migration-required contract for residual root resources. This Phase 8 work is the bulk file-move operation that makes on-disk runs compliant with the Phase 7 directory-only runtime contract.

The migration script must handle both standalone runs and batch projects by walking both run and batch roots on each host:
- forest roots: `/wc1/runs`, `/wc1/batch`
- wepp1 roots: `/geodata/wc1/runs`, `/geodata/wc1/batch`

The script should be idempotent, conflict-safe, and auditable. It must never overwrite conflicting targets silently.

## Plan of Work

### Phase 1: Implement Batch Migration Script

Implement `wepppy/tools/migrations/unroll_root_resources_batch.py` with:
- `--host {forest,wepp1}` (required)
- `--mode {dry-run,apply}` (required)
- `--roots <csv>` defaulting to host-specific run+batch roots above
- `--audit-jsonl <path>` and `--summary-json <path>`
- `--max-workers <n>` for controlled parallelism
- `--wepp1-approval-file <path>` required when `--host wepp1 --mode apply`
- `--approval-token <token>` optional second factor matching token in approval file

Script behavior:
1. Discover candidate project directories under configured roots.
2. Resolve `apply_nodir`; only `false` is eligible.
3. Discover in-scope WD-root resources by fixed patterns.
4. In dry-run: emit planned per-file and per-run records only.
5. In apply:
   - lock each run/project root for maintenance (single-run lock file)
   - move/dedup according to Phase 7 migration spec
   - on target hash mismatch, record conflict and leave both untouched
   - emit per-file and per-run records
6. Exit non-zero when any run has `error` status; conflicts are explicit but non-destructive.

### Phase 2: Forest Dry-Run Inventory

Run dry-run on forest:
- `/wc1/runs`
- `/wc1/batch`

Produce artifacts:
- `artifacts/phase8_forest_dry_run_audit.jsonl`
- `artifacts/phase8_forest_dry_run_summary.json`
- `artifacts/phase8_forest_dry_run_report.md`

Review:
- eligible run count
- planned move count by resource type
- conflicts predicted (if any)

### Phase 3: Forest Apply Migration

Run apply on forest after dry-run review. Produce:
- `artifacts/phase8_forest_apply_audit.jsonl`
- `artifacts/phase8_forest_apply_summary.json`
- `artifacts/phase8_forest_apply_report.md`

Verify:
- no in-scope WD-root resources remain on migrated eligible runs
- canonical targets exist and are readable
- conflict runs are explicitly listed for manual resolution

### Phase 4: Wepp1 Dry-Run + Approval Packet

Run dry-run only on wepp1:
- `/geodata/wc1/runs`
- `/geodata/wc1/batch`

Produce:
- `artifacts/phase8_wepp1_dry_run_audit.jsonl`
- `artifacts/phase8_wepp1_dry_run_summary.json`
- `artifacts/phase8_wepp1_approval_packet.md`

Approval packet must include:
- eligible run count
- planned move count by resource type
- predicted conflict count
- proposed maintenance window
- rollback/incident contact checklist
- explicit command that will be used for wepp1 apply

### Phase 5: Human Approval Gate (Required)

No wepp1 apply step may run until a human creates and commits:
- `artifacts/phase8_wepp1_approval.md`

Required content:
- approver name/role
- approval timestamp (UTC)
- approved command line
- approval token value (if token gating is used)
- explicit statement: “wepp1 apply approved”

Script enforcement:
- `--host wepp1 --mode apply` fails fast unless approval file exists and validates.

### Phase 6: Wepp1 Apply Migration

Run wepp1 apply only after Phase 5 approval exists and passes gate checks.

Produce:
- `artifacts/phase8_wepp1_apply_audit.jsonl`
- `artifacts/phase8_wepp1_apply_summary.json`
- `artifacts/phase8_wepp1_apply_report.md`

Verify same postconditions as forest apply.

### Phase 7: Closeout and Documentation

Update:
- `docs/work-packages/20260227_nodir_full_reversal/tracker.md`
- this plan’s living sections
- any changed migration docs/contracts

Publish:
- `artifacts/phase8_validation_log.md`
- `artifacts/phase8_findings_resolution.md`
- `artifacts/phase8_subagent_review.md`
- `artifacts/phase8_final_verification.md`

## Concrete Command Sequence

Run from `/workdir/wepppy` unless noted.

1. Implement + unit tests:
   - `wctl run-pytest tests/tools/test_migrations_* --maxfail=1`
2. Forest dry-run:
   - `python3 wepppy/tools/migrations/unroll_root_resources_batch.py --host forest --mode dry-run --audit-jsonl docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_forest_dry_run_audit.jsonl --summary-json docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_forest_dry_run_summary.json`
3. Forest apply:
   - `python3 wepppy/tools/migrations/unroll_root_resources_batch.py --host forest --mode apply --audit-jsonl docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_forest_apply_audit.jsonl --summary-json docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_forest_apply_summary.json`
4. Wepp1 dry-run:
   - `python3 wepppy/tools/migrations/unroll_root_resources_batch.py --host wepp1 --mode dry-run --audit-jsonl docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_wepp1_dry_run_audit.jsonl --summary-json docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_wepp1_dry_run_summary.json`
5. Wepp1 apply (only after approval file exists):
   - `python3 wepppy/tools/migrations/unroll_root_resources_batch.py --host wepp1 --mode apply --wepp1-approval-file docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_wepp1_approval.md --approval-token <approved-token> --audit-jsonl docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_wepp1_apply_audit.jsonl --summary-json docs/work-packages/20260227_nodir_full_reversal/artifacts/phase8_wepp1_apply_summary.json`

## Validation and Acceptance

Required validation gates:

1. `wctl run-pytest tests --maxfail=1`
2. `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
3. `python3 tools/code_quality_observability.py --base-ref origin/master`
4. `wctl check-rq-graph`
5. `wctl doc-lint --path docs/work-packages/20260227_nodir_full_reversal`
6. `wctl doc-lint --path docs/schemas`
7. `wctl doc-lint --path PROJECT_TRACKER.md`

Mandatory subagent loop:
1. `reviewer` correctness/regression
2. `test_guardian` test-quality
3. resolve findings
4. rerun until unresolved high/medium = 0

Acceptance:
- forest apply completed with explicit per-run outcomes and no silent conflicts
- wepp1 apply blocked without approval and succeeds only after explicit human approval artifact
- all required gates pass on final state

## Idempotence and Recovery

- Dry-run is always non-mutating and repeatable.
- Apply is idempotent for already migrated runs.
- Conflicts are non-destructive (`conflict_requires_manual_resolution`).
- On per-run failure, continue processing other runs and emit error status for failed run.
- Recovery from partial runs uses audit JSONL records to resume safely.

## Interfaces and Dependencies

Script interface must preserve compatibility with Phase 7 migration contract:
- source/target mapping as locked in this plan
- `apply_nodir=false` eligibility only
- conflict-on-hash-mismatch behavior
- explicit audit schema fields from Phase 7 migration spec

Dependencies:
- standard library filesystem/hash/json/concurrency modules
- existing WEPPpy helpers for `apply_nodir` resolution where available
- no runtime fallback restoration or `wepppy.nodir` imports
