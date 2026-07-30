# Final Operations and Security Review

## Metadata

- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Reviewer**: independent operations/security control agent
- **Date**: 2026-07-30 UTC
- **Reviewed checkpoint**:
  `1b412d61ab1173c53c6def06f123d124aaf8bfd1`
- **Current repository HEAD**:
  `18d7b40e38cf4a873f2fe3f20ef6efe0bd8cc6ce`
- **Implementation state**: current uncommitted SURF-14A implementation and
  tests in the shared worktree
- **Forest execution**: not performed

## Verdict

**FAIL — reject release and Forest execution.**

The reviewed checkpoint is an ancestor of the current repository HEAD, and
several controls are implemented correctly. The current implementation
nevertheless violates the accepted containment, traceback-retention, terminal
RQ-state, service-identity, and stale-state contracts. Four High and four
Medium findings remain unresolved.

The focused test suite passing does not close these findings because its RQ
dependent double does not model Redis registries, it asserts only serializer
redaction rather than stored traceback redaction, and it does not exercise the
cleanup collision/symlink boundaries, HUC service identities, pre-detection WBT
failure, PostgreSQL migration cycle, or concurrent preference writes.

## Control Results

The following controls passed review:

- `/preferences` requires login, uses the application-wide CSRF protection,
  extracts only the two preference fields, validates exact enum tokens, and
  escapes rejected values in the rendered page.
- Preference lookup is limited to `token_class=user`, binds `sub` to numeric
  User ID or exact `fs_uniquifier`, requires an active User, and rejects a
  conflicting claimed email. Service and MCP identities do not resolve an
  account.
- Account-derived creation overrides are limited to
  `unitizer:is_english` and
  `watershed.wbt:boundary_touch_behavior`; explicit unit input has precedence.
- `register_owned_run()` creates the `Run` and `runs_users` association in one
  database transaction while locking the active User row.
- The migration is additive, merges heads `7b3c068e7a1d` and
  `b7d9c3e2f1a4`, names the primary key, cascading foreign key, and both check
  constraints, and has a direct table-drop downgrade.
- WBT attempts clear both readiness timestamps and the canonical
  `subwta.tif`; the typed error retains sorted edge IDs and prevents a
  completion trigger.
- The reviewed Forest runbook has a secure custom-format backup, restore-list
  validation, enqueue quiescence, queue/worker drain, graceful worker stop,
  post-stop checks, stop-before-checkout ordering, one-off migration, exact
  schema assertions, unchanged User count, and a stop-on-failure recovery path.
  Those controls remain suitable only after the implementation findings and
  local gates below are closed.

## High Findings

### FINAL-SEC-01: Creation responses disclose internal tracebacks and exception details

`project_routes.py` calls `error_response_with_traceback()` for payload parsing
and three authentication-boundary failures. `responses.py` places the formatted
traceback in the public `error.details` field. The same route returns
`str(exc)` for run-directory failures, and the HUC route returns raw validation
or unexpected exception text in both 400 and 500 responses.

This contradicts the accepted rule that database details, paths, query text,
and stack traces remain server-side. The regular create route is reachable
through CAP, bearer-token, and cookie flows, so this is a live boundary rather
than operator-only diagnostic state.

Evidence:

- `wepppy/microservices/rq_engine/project_routes.py:243`
- `wepppy/microservices/rq_engine/project_routes.py:277`
- `wepppy/microservices/rq_engine/project_routes.py:289`
- `wepppy/microservices/rq_engine/project_routes.py:313`
- `wepppy/microservices/rq_engine/project_routes.py:351`
- `wepppy/microservices/rq_engine/responses.py:90`
- `wepppy/microservices/rq_engine/upload_huc_fire_routes.py:46`
- `wepppy/microservices/rq_engine/upload_huc_fire_routes.py:161`
- `wepppy/microservices/rq_engine/upload_huc_fire_routes.py:171`
- `tests/microservices/test_rq_engine_upload_huc_fire_routes.py:222`

Required closure:

- Return stable generic client messages, codes, and `error_id` values for
  unexpected failures.
- Keep the exception, path, and traceback only in server logs keyed by that
  same `error_id`.
- Add negative tests that inject path-bearing and traceback-bearing exceptions
  into every affected branch and prove they do not appear in the response.

### FINAL-SEC-02: Compensating cleanup is not confined to state created by the request

The SQL compensation helper deletes any `Run` matching `runid`. Both creation
paths call it after `register_owned_run()` fails even though that helper has
already rolled back its transaction. If a generated ID collides with a
preexisting SQL row whose filesystem directory is absent, compensation can
delete that unrelated row and its ownership association.

Filesystem cleanup also resolves both the supplied path and
`get_wd(runid)` through `realpath()` and then recursively removes the resolved
target. A top-level `/wc1/runs/<new-id>` symlink to a sibling run makes both
resolved values equal and passes the common-path check, allowing
`shutil.rmtree()` to delete the sibling run. No cleanup confinement or symlink
regression test exists.

Evidence:

- `wepppy/weppcloud/user_preferences.py:181`
- `wepppy/weppcloud/user_preferences.py:223`
- `wepppy/microservices/rq_engine/project_routes.py:383`
- `wepppy/microservices/rq_engine/upload_huc_fire_routes.py:53`
- `wepppy/weppcloud/utils/runid.py:8`

Required closure:

- Bind SQL compensation to a row or transaction provenance created by this
  request; never delete an arbitrary row by a colliding public run ID.
- Reject a symlinked top-level run directory and use a no-follow,
  race-resistant deletion strategy scoped to the exact newly created
  directory.
- Test preexisting SQL collision, top-level symlink-to-sibling, symlink
  replacement, canonical-path mismatch, runs-root refusal, and ordinary
  request-owned cleanup.

### FINAL-SEC-03: Controlled RQ failure re-retains a raw traceback

`build_subcatchments_rq()` removes `job.meta["exc_string"]`, saves the
controlled payload, and re-raises. The configured `WepppyRqWorker` then formats
the complete exception traceback, writes it back to `job.meta["exc_string"]`,
and saves the job. RQ also retains its normal failure representation. The HTTP
serializer currently hides the raw value when `meta.error` is present, but the
accepted contract requires this expected controlled failure not to retain a
raw traceback at all.

The controlled catch also does not write the required structured server log
containing `error_id`, run ID, and sorted edge IDs. Its status message omits
`error_id`, leaving the retained traceback as the only detailed failure
diagnostic.

Evidence:

- `wepppy/rq/project_rq.py:965`
- `wepppy/rq/rq_worker.py:240`
- `wepppy/rq/job_info.py:38`
- `tests/rq/test_job_info.py:60`

Required closure:

- Sanitize the RQ failure record and `exc_string` after the worker failure
  lifecycle, not only in the HTTP serializer.
- Emit the contract's traceback-free structured log keyed by the same
  `error_id`.
- Use a real worker/Redis integration test to prove the stored job hash,
  failure result, child and root `/jobinfo` payloads, and logs contain no raw
  traceback or path.

### FINAL-OPS-04: The stopped dependent remains in inconsistent RQ shared state

The abstraction job is enqueued with a dependency and is therefore registered
as deferred. On boundary failure the code only calls
`dependent.set_status(JobStatus.STOPPED)` and `dependent.save()`. In the
installed RQ 1.16.2 implementation, `Job.set_status()` only writes the status
field; it does not remove the job from `DeferredJobRegistry`, its dependency
sets, or its parent's dependent set. `DeferredJobRegistry.cleanup()` is a
no-op.

The unit test replaces RQ with a two-method object and therefore proves only
that the status setter was called. It does not prove terminal registry state,
an empty active tree, safe retry, or queue-drain behavior. Leaving a stopped
job in the deferred registry compromises shared-state integrity and can block
operational drain evidence.

Evidence:

- `wepppy/rq/project_rq.py:975`
- `wepppy/rq/project_rq.py:1073`
- `tests/rq/test_project_rq_mutation_guards.py:70`
- installed `rq.job.Job.set_status()` and
  `rq.registry.DeferredJobRegistry` in RQ 1.16.2

Required closure:

- Transition or cancel the dependent through an RQ-supported operation that
  atomically cleans its deferred-registry and dependency membership.
- Add real Redis evidence for child failure, stopped/canceled abstraction,
  empty active/deferred membership as defined by the contract, terminal failed
  root aggregation, no abstraction execution, and a successful retry.

## Medium Findings

### FINAL-OPS-05: HUC service and MCP creation no longer remain config-only

The accepted identity matrix preserves otherwise-authorized service and MCP
creation without an account lookup. `resolve_creation_preferences()` correctly
returns `None` for these token classes, but the HUC route treats that result as
an identity error and returns `preference_resolution_failed`. Before this
change the endpoint accepted any non-session JWT with `rq:enqueue`.

Evidence:

- `wepppy/weppcloud/user_preferences.py:114`
- `wepppy/microservices/rq_engine/upload_huc_fire_routes.py:92`
- `tests/weppcloud/test_user_preferences.py:72`

Required closure:

- Preserve the service/MCP config-only path while continuing to fail closed for
  unknown or inactive `token_class=user` identities.
- Add HUC tests for user, service, MCP, session, unknown User, and inactive User
  tokens.

### FINAL-OPS-06: Cleanup failures cannot be correlated to the returned error

The contract requires compensation failures to be logged with the same
`error_id` returned to the client. The regular and HUC paths log cleanup
failures before calling `error_response()`, which generates a new ID internally.
The cleanup helper accepts no correlation ID, and its messages include neither
run ID nor a response error ID.

Evidence:

- `wepppy/microservices/rq_engine/project_routes.py:366`
- `wepppy/microservices/rq_engine/project_routes.py:383`
- `wepppy/microservices/rq_engine/upload_huc_fire_routes.py:53`
- `wepppy/microservices/rq_engine/responses.py:40`

Required closure:

- Allocate one error ID before compensation starts, pass it through every
  cleanup log, and return it unchanged.
- Test SQL cleanup failure, filesystem cleanup failure, and both failures
  together.

### FINAL-OPS-07: A pre-detection WBT failure leaves stale edge diagnostics

Every WBT attempt is required to replace the previous edge-ID set. The current
implementation clears timestamps and `subwta.tif`, but does not clear
`_edge_hillslopes` until after `wbt.delineate_subcatchments()` succeeds. If WBT
fails before edge detection, the previous edge IDs remain persisted even though
the new attempt has no valid edge result.

Evidence:

- `wepppy/nodb/core/watershed_mixins.py:521`
- `wepppy/nodb/core/watershed_mixins.py:541`
- `tests/nodb/test_wbt_boundary_touch_behavior.py:109`

Required closure:

- Persist an empty edge-ID set at attempt invalidation before invoking WBT.
- Test a prior non-empty set followed by pre-detection failure and subsequent
  successful retry.

### FINAL-OPS-08: PostgreSQL migration and concurrency evidence is not durable

The only checked-in migration-cycle test creates `sqlite://`; it does not prove
the merge revision, cascading foreign key, named constraints, or downgrade
behavior against PostgreSQL. No test exercises `save_user_preferences()` with
concurrent first inserts or serialized complete-record updates. The ExecPlan
states that a local PostgreSQL upgrade and introspection passed, but the package
contains no command transcript or separate evidence artifact from which the
database, starting heads, exact commands, and results can be independently
audited.

Evidence:

- `tests/weppcloud/test_user_preferences_migration.py:13`
- `wepppy/weppcloud/user_preferences.py:76`
- `docs/work-packages/20260729_user_preferences_wbt_boundary/prompts/active/user_preferences_wbt_boundary_execplan.md:124`

Required closure:

- Add or retain a redacted, reproducible disposable-PostgreSQL
  upgrade/downgrade/upgrade transcript covering both starting heads, all four
  named constraints, cascade delete, missing-row behavior, and row
  preservation.
- Add deterministic PostgreSQL tests for concurrent first save and
  whole-record last-committed-write-wins update serialization.

## Validation Evidence

Executed locally without Forest access:

| Gate | Result |
| --- | --- |
| Checkpoint ancestry (`merge-base` and `--is-ancestor`) | PASS |
| Focused eight-file Python selection | PASS: 145 tests |
| `wctl run-stubtest wepppy.weppcloud.user_preferences` | PASS |
| `wctl check-test-stubs` | PASS |
| Package and active ExecPlan documentation lint | PASS |
| Scoped `git diff --check` | PASS |
| `wctl check-rq-graph` | FAIL: both generated RQ artifacts reported drift |
| Changed-file broad-exception enforcement from `1b412d61a` | FAIL: net +3 unsuppressed catches |

`wctl check-test-isolation` exited zero and ended with “No isolation issues
detected,” but also printed one failure for each of its five seeds and said
per-file isolation could not be determined. That contradictory output is not
accepted as clean durable evidence.

The RQ graph and broad-exception failures occur in the current shared worktree,
which also contains unrelated Pure UI and Command Bar changes. They are not
included in the High/Medium counts above, but both required gates must pass on
the isolated release diff before re-review. The previously recorded full-suite
result of 5,643 passed and 58 skipped was not rerun during this independent
review.

## Unresolved Count and Gate Decision

- **Unresolved High**: 4
- **Unresolved Medium**: 4
- **Unresolved Low**: 0
- **Local acceptance E2E**: **must not proceed as an acceptance gate**.
  Developer-only local diagnostics may continue while fixing the findings.
- **Forest preflight**: **must not proceed**.
- **Forest migration/canary**: **must not proceed**.
- **Release recommendation**: reject and require independent re-review.

Re-review requires all eight findings to be closed with regression evidence,
the RQ graph and broad-exception gates to pass on an isolated release diff, and
the local acceptance E2E to run only after those conditions are satisfied.
Forest remains blocked until that re-review passes. No rollback, recovery, or
security posture may be weakened to make the gates pass.
