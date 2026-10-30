# Repair WEPP admission ordering without changing valid workflows

Work in `/home/workdir/wepppy`. Implement and validate a bounded correction for:

> Rejected WEPP submissions persist inputs before admission.

This is an implementation task. Continue through investigation, the applicable repository governance steps, regression coverage, correction, and validation. Do not stop at a proposed fix when authorized work remains possible. Do not deploy, submit production jobs, change branches, install dependencies, or modify unrelated work.

## Starting evidence — reverify against the current checkout

A static review at commit `29716c1bd9a24dacf1cb45e05a11b2aa44a5378e` on `master` found this sequence in `wepppy/microservices/rq_engine/wepp_routes.py`, `_handle_run_wepp_request`:

1. Parse the request and handle optional webhook replay.
2. Call `apply_wepp_run_payload(...)` (approximately lines 156–178).
3. Return a configuration-only response for batch/base contexts (approximately lines 180–181).
4. Acquire `rq_submission_lock(..., lifecycle_key=runid)`.
5. Reconcile deferred jobs and call `ensure_no_active_wepp_job(...)` (approximately lines 189–198).
6. Clear task timestamps, preallocate/persist a job receipt and hint, and enqueue.

`apply_wepp_run_payload` persists configuration before step 5. Thus a request with changed valid parameters can modify controller state and subsequently return HTTP 409 because a job is active or the submission lock is busy.

The existing execution can consume those changes: jobs pass `runid`, and stages such as `_prep_slopes_rq` and `_prep_soils_rq` in `wepppy/rq/wepp_rq_stage_prep.py` reload controller state. This is a confirmed static ordering path, not a runtime reproduction of mixed scientific results. Establish a deterministic regression before claiming runtime confirmation.

Starting consumers sharing the handler:

- `POST /api/runs/{runid}/{config}/run-wepp`
- `POST /api/runs/{runid}/{config}/run-wepp-watershed`
- `POST /api/runs/{runid}/{config}/prep-wepp-watershed`

Reverify these names and all indirect callers; line numbers may have moved.

## Instructions and authority

Read root and nearest applicable `AGENTS.md` files before edits, including rq-engine, NoDb, tests, and any documentation directories you touch. Apply relevant skills, particularly `wepppy-tester` for verification and `docs-maintainer` for repository documentation.

Read the relevant current canonical contracts, including:

- `docs/standards/contract-first-change-standard.md`
- `docs/standards/hardening-lifecycle-standard.md`, especially failure-class assessment and working-behavior authority
- `docs/schemas/rq-response-contract.md`
- `docs/schemas/rq-webhook-contract.md`
- `docs/schemas/nodb-persistence-concurrency-contract.md`
- `docs/standards/generated-artifact-validation-standard.md`
- Any current submission/admission/lifecycle contracts identified by the nearest guidance and implementation.

The operator requests this bounded outcome: an execution submission rejected by WEPP admission must not persist its proposed input changes or change the inputs consumed by already-admitted work. Preserve valid configuration-only batch/base behavior.

Classify whether this repairs conformance to an existing contract or changes intended behavior. Do not assume a governance exemption. If the contract-first checkpoint applies, follow its actual requirements, including independent reviews and the ancestor commit. This prompt does not independently grant commit authority or waive a required checkpoint. Prepare concrete authorized work before raising a genuinely missing approval; explain the exact rule and remaining action. Do not request repeat approval for the bounded correction already requested here.

Use an active ExecPlan if required by scope/complexity. Read the ExecPlan template before creating one, identify the plan being executed, and keep its tracker current. Do not repurpose an unrelated active package or amend closed historical packages.

Record initial branch, revision, and working-tree status. The review checkout already contained unrelated roads-program edits and untracked artifacts; preserve all pre-existing work. Ignore dirty `wepppy/weppcloud/routes/usersum/generated/docs_index.json` as instructed.

## Required behavior and scope limits

For ordinary execution submissions, establish admission before applying requested inputs. Use the existing submission coordination mechanism to protect the relevant check/mutation/enqueue sequence; a precheck followed by release and later mutation is insufficient.

Preserve:

- Authentication, authorization, scopes, prerequisite/capability checks, canonical errors, and established response shapes.
- Configuration-only behavior for batch/base projects; these valid saves must not accidentally become execution submissions or require an inappropriate active-job gate.
- Optional webhook replay semantics, including replay without reapplying inputs or enqueuing duplicates.
- Job preallocation, durable discovery receipts, job hints, deferred-work reconciliation, lifecycle coordination, lease checkpoints, and ownership-safe release.
- Sparse payload handling, valid booleans/zero values, supported legacy fields, and current parameter semantics.
- Existing successful input preparation and model execution paths.

Distinguish proposed-input mutation from permitted reconciliation of prior orchestration state. Do not require all Redis bytes to remain identical when reconciliation legitimately updates prior job state. Rejected submissions must not clear completion timestamps, replace active-job receipts/hints, or publish proposed input changes merely because they reached the submission path.

This fix is not a mandate for full distributed transactions, immutable run snapshots, a new queue/service/database, broad parser cleanup, or automatic rollback after an admitted request encounters a later enqueue/storage failure. Document those separate boundaries accurately. Do not bundle the review's failed-singleton-edit, malformed-body, or RedisPrep snapshot findings into this task unless evidence shows a minimal part is indispensable to this correction; explain any necessary scope adjustment first.

## Investigation and design

1. Trace the shared handler, `apply_wepp_run_payload`, all three endpoints, webhook submission wrapper, and submission/lifecycle leases. Inspect workers that reload state.
2. Inspect `wepppy/rq/submission_recovery.py`, WEPP active-work/reconciliation helpers, and relevant tests. Establish what acquires locks, what writes files or metadata, and what can raise or replay.
3. Retain a compact consumer/state matrix: dependency path, context, evidence, and disposition (`confirmed defect`, `verified unaffected`, or `unresolved`). Search for equivalent mutations-before-admission within the authorized WEPP submission family, including indirect callers. Do not claim repository-wide coverage from this bounded search.
4. Separate valid states from payload combinations: fresh/never-run project, completed prior run, active root or child, recoverable deferred prior work, batch/base project, supported legacy missing hints, and malformed/ambiguous prior association.
5. Choose the smallest structural correction. State the intended critical-section boundary and why it closes the interleaving. Assess whether moving payload work under the lease affects its duration, renewal/checkpoints, or lock ordering. Do not hold a submission lock across model execution or remote computation.
6. Document the normative rule and concise rationale in the appropriate current canonical contract, following required sequencing. Update affected operator/developer/user documentation proportionately.

## Regression and acceptance evidence

Tests are authorized for this implementation task. Use canonical `wctl` tooling and meaningful state assertions, not source-order assertions.

Required cases:

1. **Active-job rejection, all shared endpoints:** submit changed valid inputs while existing work is active. Assert canonical 409, no new enqueue, unchanged persisted proposed-input fields, and preserved active-job receipt/hint and completion metadata except explicitly permitted reconciliation effects.
2. **Busy submission lease:** same assertions when lease acquisition fails. Prove payload mutation did not run; do not only assert the status code.
3. **Concurrent submissions:** controlled interleaving establishes that admission and mutation cannot be crossed by competing submissions. After A is accepted, rejected B cannot alter A's preparation inputs. Cover an active descendant where the dispatcher parent has already finished if this is part of the existing admission contract.
4. **Successful normal submission:** accepted parameters persist, the same preallocated job identity is used, and the expected response is returned.
5. **Batch/base configuration-only saves:** preserve updates and existing response without enqueue. Cover actual base detection variants and batch membership used by the handler.
6. **Webhook replay and new submission:** preserve replay identity/no duplicate mutation, admission conflict behavior, and the existing callback contract.
7. **Failures inside the admitted section:** validation/persistence/enqueue exceptions release only the owned lease and keep existing error contracts. Do not assert rollback guarantees the implementation does not provide.
8. **Deferred recovery and lifecycle exclusion:** existing recovery continues to work and mismatched/ambiguous work remains fail-closed; timestamp/receipt updates happen only at their appropriate boundary.

At least one test must exercise real NoDb persistence and reload rather than replacing `apply_wepp_run_payload` with a stub. Verify the filesystem bytes or reloaded semantic fields after rejection. Follow the contract-first standard's unmocked-boundary requirements; mocked queue/lease tests alone cannot prove filesystem or actual coordination behavior.

For the consumer-facing consequence, use a disposable representative fixture and the real preparation path where feasible: accept input A, reject changed input B, generate the relevant file under `wepp/runs/`, parse the exact parameter consumed downstream, and prove it still reflects A. Avoid an expensive full model run if prepared-input readback establishes the changed boundary. If the required environment is unavailable, record exactly what remains unverified rather than treating mocks as equivalent.

Starting test locations:

- `tests/microservices/test_rq_engine_wepp_routes.py` — existing single-flight and busy-lock tests around lines 1404–1459 only checked response behavior in the review.
- Tests of `wepp_run_payload`, submission recovery, WEPP job reconciliation, and relevant preparation stages; discover current paths.
- `tests/nodb/test_base_boundary_characterization.py` for persistence fixture patterns, without expanding this repair into a NoDb redesign.

Run focused regressions first, then required repository checks, including the substantive-code pre-handoff pytest gate. Run graph/catalog/live-tree checks if queue wiring actually changes; avoid unnecessary queue wiring changes. Run frontend checks only if frontend code changes. Lint affected documentation. Report commands and actual outcomes, including environment blockers, without claiming skipped tests passed.

## Handoff

Provide:

- Confirmed cause and exact corrected boundary.
- Changed files and canonical contract section documenting the rule/rationale.
- Consumer/state coverage matrix and any unresolved cases.
- Regression results and prepared-input evidence, clearly separating executed tests from static inspection.
- Compatibility impact, remaining risks, and whether any required governance/validation step remains blocked.

Do not claim that this repair solves all concurrent editing, all enqueue failures, or universal execution-input immutability. Close the specific admission-ordering defect with evidence.
