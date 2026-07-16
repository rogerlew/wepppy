# Repair and Prevent Copied Batch Identity in Interactive Forks

This ExecPlan is a living document maintained under
`docs/prompt_templates/codex_exec_plans.md`. The sections `Progress`,
`Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must
remain current while work proceeds.

## Purpose / Big Picture

An interactive WEPPcloud run cloned from a Batch Runner leaf currently retains
serialized Batch Runner identity. On `wepp1`, run `subsequent-hotbed` therefore
cannot enqueue WATAR: the ash route returns `Set ash inputs for batch processing`.
After this plan, a guarded CLI repairs that run without rebuilding scientific
inputs, and the normal fork worker prevents future interactive destinations from
inheriting batch identity. A human can verify success by loading the repaired Ash
controller and observing `run_group is None`, then submitting ash inputs and
receiving a job ID rather than the batch input-only message.

## Progress

- [x] (2026-07-16 17:15 UTC) Captured production path, route predicate, and
  serialized identity evidence from `wepp1`.
- [x] (2026-07-16 17:18 UTC) Recorded the run-data compatibility and regression
  plan in `docs/ui-docs/weppcloud-project-forking.md` before code edits.
- [x] (2026-07-16 17:22 UTC) Created the work package and active ExecPlan.
- [x] (2026-07-16 17:30 UTC) Implemented a dry-run-first repair CLI with
  validation, timestamped backup, rollback, atomic writes, verification, and
  root-scoped cache invalidation; focused tests pass.
- [x] (2026-07-16 17:31 UTC) Dry-ran, backed up, repaired, invalidated cache,
  and verified `subsequent-hotbed` on `wepp1`.
- [x] (2026-07-16 17:34 UTC) Normalized copied root NoDb identity and batch
  metadata in the fork helper with integration regressions.
- [x] (2026-07-16 17:55 UTC) Completed targeted validation and independent
  code/QA/security reviews with no unresolved high or medium findings.
- [x] (2026-07-16 18:04 UTC) Passed the full suite and static/documentation gates,
  closed package records, and archived this ExecPlan under `prompts/completed/`.

## Surprises & Discoveries

- Observation: The route message is emitted after ash inputs are parsed and
  persisted, so the failed-looking attempt changed ash settings but enqueued no
  WATAR job.
  Evidence: `ash_routes.py` sets `ash_depth_mode` before testing `run_group`.
- Observation: The visible primary run directory is correct, while 13 root NoDb
  payloads and `run_metadata.json` still describe batch leaf `WA-10`.
  Evidence: `jq` inspection on `wepp1` at 2026-07-16 17:15 UTC.
- Observation: Whole-run `clear_nodb_file_cache` can resolve `_pups` symlinks
  outside the primary run and invalidate those external cache keys.
  Evidence: The production manifest listed two source-batch cache paths; the
  `_pups` content hash and all source files were unchanged.

## Decision Log

- Decision: Normalize destination state instead of weakening route batch checks.
  Rationale: Native Batch Runner leaves require their serialized identity; the
  defect is introduced only when fork copies that identity into a primary run.
  Date/Author: 2026-07-16, Roger Lew and Codex.
- Decision: The repair tool is dry-run-first and rejects any non-batch group.
  Rationale: Production file mutation must fail closed and remain scoped to the
  confirmed incident class.
  Date/Author: 2026-07-16, Codex.
- Decision: Root `*.nodb` files are in scope and `_pups/` is excluded.
  Rationale: The destination is interactive, but child workspaces may have valid
  independent orchestration identity.
  Date/Author: 2026-07-16, Codex.
- Decision: Repair cache invalidation is performed once per changed root NoDb
  using `pup_relpath`, not with the whole-run cache clearer.
  Rationale: Exact scopes avoid following child-workspace symlinks into source
  cache keyspaces while still invalidating every modified controller.
  Date/Author: 2026-07-16, Codex.

## Outcomes & Retrospective

The production run is repaired and eligible for WATAR submission. The guarded
repair CLI and permanent fork normalization are implemented locally. Complete
preflight, cross-file identity agreement, atomic forward/rollback publication,
and scoped cache-only recovery were added through review. Both independent reviews
pass with no unresolved high or medium findings. Validation passed 55 focused tests,
4,948 full-suite tests, documentation lint, Python compilation, broad-exception
enforcement, and `git diff --check`. The permanent patch was not deployed because
deployment was explicitly outside this package; the one-run repair is complete.

## Context and Orientation

WEPPcloud persists each run controller as a JSON/jsonpickle `.nodb` file. The
fields `_run_group` and `_group_name` identify grouped runs such as Batch Runner
leaves. `wepppy/microservices/rq_engine/ash_routes.py` deliberately avoids
enqueuing WATAR when `Ash.run_group == "batch"`. The fork worker in
`wepppy/rq/project_rq_fork.py::prepare_fork_run` uses rsync to copy a source run,
then rewrites paths in root `.nodb` files. It does not currently clear copied
group fields or remove source `run_metadata.json`.

The affected production route is
`/weppcloud/runs/subsequent-hotbed/disturbed9002-wbt-mofe/`. Its host path is
`/geodata/wc1/runs/su/subsequent-hotbed`; its container path is
`/wc1/runs/su/subsequent-hotbed`. The source batch name is
`nasa-roses-202606-psbs`. A NoDb cache exists in Redis, so file mutation must be
followed by `clear_nodb_file_cache("subsequent-hotbed")` and a fresh controller
read.

## Plan of Work

Create `tools/repair_forked_run_identity.py`. It accepts one explicit run root,
the expected primary run ID, and optionally the expected batch name. Without
`--apply` it only reports a plan. Apply mode validates every root `.nodb` JSON
document before writing, rejects non-batch identity or batch-name disagreement,
creates one timestamped backup directory, atomically replaces only changed root
payloads, removes active batch `run_metadata.json` after backing it up, verifies
the resulting files, and optionally clears the run's Redis NoDb cache. Repeated
execution on a repaired run must be a successful no-op.

Add `tests/tools/test_repair_forked_run_identity.py` for dry-run, apply,
`_pups/` exclusion, rejection-before-write, metadata backup/removal, and
idempotence. Run the CLI in dry-run mode against production first. Copy the
locally tested script to `/tmp` on `wepp1`, execute it inside the `weppcloud`
container so `/wc1` and Redis settings match runtime, and apply only after the
dry-run identifies the expected 13 controllers and batch name. Verify the backup
manifest, cleared cache, root file state, and a freshly loaded `Ash` object.

Then add a shared normalization helper in
`wepppy/rq/project_rq_fork.py`. Call it from `prepare_fork_run` immediately after
path rewriting and before destination controllers can be hydrated. It must use
the same root-only, fail-closed JSON mutation contract and remove only batch
execution metadata. Extend `tests/rq/test_project_rq_fork.py` with a source batch
fixture proving destination roots are interactive while `_pups/` remains byte
identical. Do not change route, queue, authorization, or native batch behavior.

Update the package tracker throughout. After implementation, request independent
code and QA reviews, complete the dedicated security artifact, remediate all
medium/high findings, run targeted and full gates, close package records, and
move this plan to `prompts/completed/` with final outcomes.

## Concrete Steps

Work from `/home/workdir/wepppy` locally.

1. Implement and test the repair CLI:

       wctl run-pytest tests/tools/test_repair_forked_run_identity.py

2. Verify production host/path and run dry-run then apply inside the runtime
   container. The exact copied script path and backup directory must be recorded
   in the tracker artifact.

3. Implement permanent fork normalization and run:

       wctl run-pytest tests/rq/test_project_rq_fork.py
       wctl run-pytest tests/tools/test_repair_forked_run_identity.py

4. Run required gates:

       wctl run-pytest tests --maxfail=1
       wctl doc-lint --path docs/ui-docs/weppcloud-project-forking.md
       wctl doc-lint --path docs/work-packages/20260716_fork_batch_identity_normalization
       python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
       git diff --check

No frontend or queue wiring changes are planned, so npm and RQ graph gates are
not required unless the actual diff expands into those surfaces.

## Validation and Acceptance

The CLI tests must prove no writes in dry-run mode, atomic backed-up changes in
apply mode, no recursion into `_pups/`, fail-closed handling of malformed or
non-batch state, and idempotent repeat execution. The fork regression must fail
against the old implementation because the destination retains `batch`, and pass
after the helper clears both group fields and removes batch metadata.

Production acceptance requires all of the following: hostname is `wepp1`; the
only target is `/wc1/runs/su/subsequent-hotbed`; the expected batch name is
`nasa-roses-202606-psbs`; a timestamped backup and manifest exist; no root
controller reports non-null `_run_group` or `_group_name`; `_pups/` hashes are
unchanged; `run_metadata.json` is absent from the active root but present in the
backup; the NoDb cache clear succeeds; and a fresh `Ash.getInstance` reports
`run_group=None`. WATAR itself is not automatically submitted because that would
use the operator's saved UI choices; Alex can submit it after eligibility is
restored.

## Idempotence and Recovery

Dry-run is the default. Apply validates the complete change set before creating
backups or writing. Each replacement is written through a same-directory
temporary file and `os.replace`. If mutation fails, restore all already-modified
files from the timestamped backup and report a nonzero exit. If cache clearing
fails after verified file changes, retain the repaired files and report the
explicit cache error; retry only the cache clear. Re-running the tool after a
successful repair reports no changes and creates no second backup.

The production rollback is to copy the backup files and `run_metadata.json` back
to the run root, clear the run's NoDb cache, and verify the original batch fields.
Do not use rollback merely because the permanent code has not yet been deployed;
the repaired primary run is intentionally interactive.

## Artifacts and Notes

Production evidence will be recorded in
`artifacts/2026-07-16_wepp1_repair.md`. Review evidence will be recorded in
`artifacts/2026-07-16_code_review.md`, `artifacts/2026-07-16_qa_review.md`, and
`artifacts/2026-07-16_security_review.md`.

## Interfaces and Dependencies

The repair CLI must use only the Python standard library for inspection, backup,
and atomic writes. Runtime cache clearing may import
`wepppy.nodb.base.clear_nodb_file_cache` only when explicitly requested after
apply. The permanent fork helper remains internal to
`wepppy.rq.project_rq_fork`; no public API or stub surface is added. Existing
`jsonpickle` payload shape is treated as a JSON mapping whose controller state is
under `py/state`; a legacy top-level state mapping may be accepted only when the
same explicit fields are present.

Revision note (2026-07-16 17:22 UTC): Initial plan created after the operator
expanded scope from one-run repair to permanent fork normalization.

Revision note (2026-07-16 17:34 UTC): Recorded the completed production repair,
permanent fork implementation, focused test evidence, and the cache-scope safety
finding that narrowed the CLI to changed root files.

Revision note (2026-07-16 18:04 UTC): Recorded review-driven transaction, metadata,
path, and recovery hardening; final production dry-run; full validation; dual review
passes; and package closure.
