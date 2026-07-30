# Immutable Final Operations and Security Re-review

## Metadata

- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Reviewer**: independent operations/security control agent
- **Date**: 2026-07-30 UTC
- **Ratified contract checkpoint**:
  `1b412d61ab1173c53c6def06f123d124aaf8bfd1`
- **Reviewed implementation checkpoint**:
  `b593fb1d8595f6c3c9862ce773def31d372d787c`
- **Implementation parent**:
  `e861aae36fda0fcf851fc864dcb1e25d9282db77`
- **Prior review**:
  `artifacts/2026-07-30_final_ops_security_review.md`
- **Prior review SHA-256**:
  `6ce034ec4768ea441be7a55db6d03d41e5eab1792a5debd758eb54dd998c444f`
- **Live acceptance evidence supplied during review**:
  root job `0734dcbc-dd03-4c28-98f4-cb42ea64170c`, run
  `rock-ribbed-triplicate`
- **Forest or production access/mutation by this review**: none

This review inspected the immutable Git tree directly. The selected
implementation, test, and retained-evidence paths were byte-identical to
`b593fb1d8` when the independent focused checks ran. Unrelated shared-worktree
changes were excluded. No implementation file was modified, and the original
FAIL artifact was retained unchanged.

## Verdict

**FAIL — reject further acceptance mutation and Forest execution.**

Seven of the eight prior findings are closed. `FINAL-OPS-08` remains partially
open at Medium severity because the retained PostgreSQL evidence does not
perform the ratified fresh and Alembic-graph-level
upgrade/downgrade/upgrade cycle. It records that graph-level relative
downgrade failed with `Ambiguous walk`, then substitutes direct calls to the
revision's `downgrade()` and `upgrade()` bodies. The authoritative contract was
not amended and independently approved to accept that substitute.

New live evidence also establishes a High acceptance blocker,
`REREVIEW-OPS-09`. An existing run completed delineation with eight
boundary-touching hillslopes under its persisted `warn` value, while the user
expected the account's `Stop with an error` choice to govern that delineation.
The ratified new-run-only snapshot contract intentionally does not do this.
Applying a mutable account preference at delineation would cross an
authentication, authorization, shared-run, and asynchronous-execution
boundary that is not yet specified or tested.

The database evidence is materially stronger than at the prior review: five
real PostgreSQL tests passed without a skip, the merge upgrade and exact
constraints were observed, the direct PostgreSQL DDL body cycle succeeded,
and concurrency, cascade, ownership, receipt confinement, and collision
preservation are tested. Those controls reduce the residual issue to Medium,
but they do not close the original recovery-validation gate.

**Unresolved prior findings**: 0 High, 1 Medium, 0 Low.

**New unresolved findings**: 1 High, 0 Medium, 0 Low.

The safe scope reduction is local contract/ADR amendment, implementation and
regression work, migration-evidence remediation, and a new immutable
re-review. No break-glass justification exists for weakening identity,
run-authorization, asynchronous snapshot, rollback, or migration-evidence
requirements.

## Prior Finding Disposition

| Prior finding | Prior severity | Disposition at `b593fb1d8` |
| --- | --- | --- |
| `FINAL-SEC-01`: creation responses disclose internal tracebacks and exception details | High | **Closed** |
| `FINAL-SEC-02`: compensating cleanup is not confined to request-created state | High | **Closed** |
| `FINAL-SEC-03`: controlled RQ failure re-retains a raw traceback | High | **Closed** |
| `FINAL-OPS-04`: stopped dependent remains in inconsistent RQ shared state | High | **Closed** |
| `FINAL-OPS-05`: HUC service and MCP creation no longer remain config-only | Medium | **Closed** |
| `FINAL-OPS-06`: cleanup failures cannot be correlated to the returned error | Medium | **Closed** |
| `FINAL-OPS-07`: pre-detection WBT failure leaves stale edge diagnostics | Medium | **Closed** |
| `FINAL-OPS-08`: PostgreSQL migration and concurrency evidence is not durable | Medium | **Open — partially remediated** |

## New High Finding

### REREVIEW-OPS-09 — High: existing-run preference authority is undefined and the clarified stop policy is not enforced

The parent operator supplied the following live evidence while this review was
in progress:

- root job `0734dcbc-dd03-4c28-98f4-cb42ea64170c` belongs to run
  `rock-ribbed-triplicate`;
- both children finished;
- delineation found eight edge hillslopes and emitted a warning;
- the current owner preference row is `unit=si` and `boundary=error`;
- the run's persisted `watershed.nodb` value is `boundary=warn`;
- the run was created at 07:01 and delineated at 07:23; and
- the user explicitly clarified that this delineation should stop because
  their selection is `Stop with an error`.

This reviewer did not access the live system or Forest. The supplied timestamps
and current row do not independently prove when the preference changed. They
do prove a normative mismatch: the user now requires an account preference to
govern an existing run at delineation time, while the ratified contract and
implementation apply account preferences only during new-project creation.
Under the current contract, the persisted run value correctly remains `warn`;
under the clarified expectation, the safety choice is not enforced and
downstream work can complete.

This cannot be repaired safely by having an RQ worker read the current
preference row. That would leave several authority and integrity questions
unresolved:

- An existing run may be owned, shared, forked, legacy/unowned, or accessed by
  a service/MCP principal. The controlling account must be explicit.
- A viewer's preference must not silently mutate another owner's project.
- The initiating principal must have current run mutation/delineation
  authority, not merely an authenticated account.
- Account state may change between HTTP enqueue and worker execution. A worker
  lookup would make results timing-dependent and non-reproducible.
- Retries must not silently resolve a different account value than the
  original authorized action.
- Any effective update to `watershed.nodb` must use the canonical NoDb lock and
  preserve run-scoped audit/recovery evidence.

Required closure:

1. Amend the authoritative contract and ADR to define whether the controlling
   value comes from an explicit operation choice, the authorized initiating
   user, the run owner, or existing persisted run state, including exact
   precedence.
2. Define existing, shared, forked, legacy/unowned, anonymous, service, MCP,
   and session behavior. Fail closed where no authorized account-bearing actor
   can be bound.
3. At the authenticated enqueue boundary, verify run mutation authority and
   snapshot only the bounded effective policy plus stable actor identity.
   Do not defer account lookup to the worker.
4. Carry the snapshot through the RQ contract, persist it under the canonical
   run/NoDb lock before WBT execution, and make retries deterministic.
5. Retain correlated audit evidence identifying the actor, run, job, prior
   policy, effective policy, and outcome without retaining credentials or
   tokens.
6. Add regression coverage for owner-initiated existing-run delineation,
   preference changes after enqueue, retry, shared viewer denial, owner/shared
   precedence, service/MCP behavior, and the exact eight-edge stop path.
7. Run a new non-Forest acceptance canary proving `error` produces the
   controlled terminal failure and `warn` preserves the compatible path.

The recommended safety direction is to resolve and authorize the initiating
user synchronously at the delineation request boundary, then persist a bounded
snapshot before enqueue/worker mutation. That recommendation is not approval
to implement it until the owner/shared-run semantics and precedence are
ratified.

## Closed High Findings

### FINAL-SEC-01 — Closed: public creation failures are sanitized and correlated

The regular creation boundary now allocates an `error_id` before logging and
returns stable generic details for unexpected payload, authentication,
preference-resolution, run-directory, `Ron`, and ownership failures. It no
longer calls `error_response_with_traceback()` or places `str(exc)` into those
public responses
(`wepppy/microservices/rq_engine/project_routes.py`, lines 251-477).

The HUC path returns generic validation and unexpected-failure messages while
logging the internal exception under the response correlation ID
(`wepppy/microservices/rq_engine/upload_huc_fire_routes.py`, lines 198-232).
The remaining `UploadError` response is the existing bounded client-validation
contract, not an unexpected exception boundary.

Regression tests inject traceback- and path-bearing failures into payload,
bearer, session, expired-token reauthorization, run-directory, HUC validation,
preference identity, and outer upload paths and reject disclosure
(`tests/microservices/test_rq_engine_project_routes.py`, lines 278-377;
`tests/microservices/test_rq_engine_upload_huc_fire_routes.py`, lines 239-277
and 352-373).

The source behavior and passing focused checks close the prior response
disclosure path.

### FINAL-SEC-02 — Closed: SQL and filesystem compensation are provenance-bound

`register_owned_run()` now returns an immutable receipt containing the exact
database primary key, run ID, configuration, and owner ID. SQL compensation
selects and deletes only a row matching every receipt field and verifies the
owner association before deletion
(`wepppy/weppcloud/user_preferences.py`, lines 218-281). The regular route
does not attempt arbitrary run-ID SQL deletion after an atomic registration
rollback. The HUC route retains the receipt and uses it only after successful
registration.

Filesystem cleanup now requires the lexical canonical target under the primary
runs root, rejects the runs root, uses `lstat()` to reject top-level symlinks
and non-directories, and refuses deletion unless Python reports the
file-descriptor-based symlink-safe `rmtree` implementation
(`wepppy/weppcloud/user_preferences.py`, lines 197-215).

Regression coverage proves:

- ordinary request-owned directory deletion;
- top-level symlink rejection;
- replacement-race containment;
- canonical-path mismatch and runs-root refusal;
- exact receipt deletion; and
- preservation of a preexisting colliding PostgreSQL `Run`.

Evidence:
`tests/weppcloud/test_user_preferences.py`, lines 120-193, and
`tests/weppcloud/test_user_preferences_postgres.py`, lines 232-308.

The focused run exercised the PostgreSQL tests without skips. This closes the
unconfined SQL and sibling-directory deletion paths.

### FINAL-SEC-03 — Closed: controlled RQ state and diagnostics are traceback-free

`build_subcatchments_rq()` is not wrapped by the generic exception-log
decorator. Its typed catch stores the bounded error payload and `error_id`,
removes any prior `exc_string`, emits a structured traceback-free log with run
ID and sorted edge IDs, cancels dependents, publishes the bounded status
message, and re-raises for RQ failure state
(`wepppy/rq/project_rq.py`, lines 924-1022).

`WepppyRqWorker` recognizes this controlled payload in both failure callbacks.
It passes only the authorized message to RQ's superclass failure handler,
persists only that message in metadata, emits the structured correlated log,
and does not invoke the generic traceback formatter
(`wepppy/rq/rq_worker.py`, lines 218-295).

The real Redis/RQ tests inspect the failed job, metadata, retained
`exc_info`/failure representation, failed registry, root/child aggregation,
public `/api/jobinfo/{job_id}`, and structured log. They reject `Traceback` and
the source path and require the same `error_id`, run ID, and sorted edge IDs
(`tests/rq/test_wbt_controlled_failure_integration.py`, lines 100-205).

The independent focused run exercised these tests against Compose Redis
without skips. This closes raw controlled-failure retention.

### FINAL-OPS-04 — Closed: canceled dependent has consistent Redis/RQ state

`_cancel_deferred_job()` batches removal from `DeferredJobRegistry`, detaches
the dependency from each parent's dependent set, deletes the dependency set,
and invokes RQ cancellation in one Redis pipeline
(`wepppy/rq/project_rq.py`, lines 197-213).

The real Redis tests prove that the dependent is `canceled`, absent from the
deferred registry, has no dependency IDs, is absent from the parent dependent
set, and is present in `CanceledJobRegistry`. The full test tree proves that
abstraction does not execute, root aggregation is terminal and failed, public
data is sanitized, and a subsequent build/abstraction pair finishes with an
empty deferred registry
(`tests/rq/test_wbt_controlled_failure_integration.py`, lines 66-97 and
140-215).

This satisfies the prior finding's explicit allowance for a supported
transition **or cancellation** and closes the shared-state integrity defect.
Any separate user-visible status-contract question is outside this prior
operations finding and does not weaken the proven Redis containment.

## Closed Medium Findings

### FINAL-OPS-05 — Closed: HUC service/MCP compatibility is preserved

The HUC boundary accepts a `None` account snapshot only for `service` and
`mcp`, leaving those callers on configuration defaults. Other account-bearing
identities fail closed
(`wepppy/microservices/rq_engine/upload_huc_fire_routes.py`, lines 100-122).

HUC route tests cover user snapshotting, service, MCP, session rejection, and
unknown-user failure
(`tests/microservices/test_rq_engine_upload_huc_fire_routes.py`, lines
186-256). The real PostgreSQL identity test separately proves that unknown,
missing-subject, conflicting-email, and inactive users raise
`PreferenceIdentityError`
(`tests/weppcloud/test_user_preferences_postgres.py`, lines 232-273).

Because inactive and unknown identities enter the same typed HUC failure
boundary, the route and real-resolver evidence compose without an untested
production branch. The compatibility regression is closed.

### FINAL-OPS-06 — Closed: compensation logs reuse the response error ID

Regular creation allocates one ID before compensation, passes it to every
cleanup log, and returns it unchanged
(`wepppy/microservices/rq_engine/project_routes.py`, lines 430-477).

HUC cleanup accepts the ID as an argument and attaches it, together with run
ID, to both SQL and filesystem failure logs
(`wepppy/microservices/rq_engine/upload_huc_fire_routes.py`, lines 48-68).
All relevant callers allocate the ID before cleanup and pass the same value to
`error_response()`.

Regression tests prove correlation for regular filesystem cleanup and HUC SQL,
filesystem, and combined cleanup failures
(`tests/microservices/test_rq_engine_project_routes.py`, lines 440-479;
`tests/microservices/test_rq_engine_upload_huc_fire_routes.py`, lines
376-425).

The correlation gap is closed.

### FINAL-OPS-07 — Closed: every WBT attempt invalidates prior edge diagnostics

The WBT branch persists an empty `_edge_hillslopes` set under the controller
lock before calling `delineate_subcatchments()`. Attempt entry also removes
both readiness timestamps and the canonical raster
(`wepppy/nodb/core/watershed_mixins.py`, lines 527-557).

The regression test starts with non-empty edge IDs, fails before raster/edge
detection, and proves empty IDs, no raster, both timestamps invalidated, and no
completion timestamp
(`tests/nodb/test_wbt_boundary_touch_behavior.py`, lines 189-212). The adjacent
warn, error, and no-edge tests prove subsequent successful delineation
replaces the set deterministically and writes completion only on success.

The stale diagnostic state is closed.

## Open Medium Finding

### FINAL-OPS-08 — Open: PostgreSQL runtime proof improved, migration recovery proof remains incomplete

The following parts of the prior finding are now closed:

- The checked-in PostgreSQL suite proves all four named constraints and
  cascading delete.
- A barrier-controlled two-writer test proves the bounded first-insert retry
  leaves one complete row.
- A deterministic two-thread test proves existing-row `FOR UPDATE`
  serialization and whole-record last-committed-write-wins behavior.
- Real PostgreSQL identity, ownership, receipt-bound deletion, and run-ID
  collision preservation tests pass.
- The retained evidence names the disposable database, both starting parent
  revisions, merge revision, exact observed constraints, invalid-token
  rejection, row preservation, cascade, and database cleanup.
- The direct migration-body unit cycle passes.

Evidence:
`tests/weppcloud/test_user_preferences_postgres.py`, lines 74-308;
`tests/weppcloud/test_user_preferences_migration.py`, lines 13-43; and
`artifacts/2026-07-30_local_postgresql_redis_evidence.md`.

The following required recovery evidence remains absent:

1. The repository's historical graph could not bootstrap an empty PostgreSQL
   database, so the retained run substituted a representative application
   schema stamped at both parents. That does not execute the contract's
   required fresh path.
2. The graph-level upgrade succeeded, but graph-level relative downgrade
   failed with `Ambiguous walk`. The evidence then called only the new
   revision's `downgrade()` and `upgrade()` bodies through Alembic
   `Operations`; it did not prove a supported graph-level downgrade and
   re-upgrade.
3. The retained artifact summarizes setup, stamping, introspection, direct
   body execution, and teardown but does not retain the exact redacted commands
   for those operations. It also does not explicitly demonstrate missing-row
   service behavior in the PostgreSQL transcript.
4. The ratified contract still requires the fresh and two-head
   upgrade/downgrade/upgrade evidence. The discovered history limitation and
   direct-body substitute were documented in the ExecPlan, but the
   authoritative contract was not amended and independently approved.

The reviewed migration is additive, and the retained Forest procedure uses a
validated backup plus nondestructive application rollback. Those controls
limit blast radius and are why this remains Medium rather than High. They are
not a substitute for resolving the accepted migration/recovery evidence
contract before Forest execution.

Required closure is one of:

- retain a redacted, reproducible PostgreSQL transcript using reviewed,
  explicit Alembic targets that performs the accepted graph-level cycle and
  proves the required fresh/two-head, constraint, cascade, missing-row, and row
  preservation outcomes; or
- amend the authoritative contract to document the historical bootstrap and
  merge-downgrade limitations, the exact replacement evidence, the
  nondestructive rollback posture, and rejected alternatives, then obtain the
  required independent checkpoint approval.

After either path, create a new immutable implementation/documentation
checkpoint and obtain a new independent re-review. Do not weaken backup,
quiescence, coordinated restart, schema verification, or post-action review
controls.

## Validation and Evidence Assessment

The following exact-checkpoint evidence is accepted:

| Gate or evidence | Result |
| --- | --- |
| Checkpoint object, parent, and contract ancestry | PASS |
| Original FAIL artifact retained at recorded SHA-256 | PASS |
| Selected source/test/evidence files match `b593fb1d8` | PASS |
| Isolated RQ dependency graph gate | PASS |
| Isolated broad-exception changed-file gate | PASS: delta 0 |
| Exact implementation diff check | PASS: clean |
| Package documentation lint before re-review artifacts | PASS: 14 of 14 |
| Isolated affected WBT/RQ selection | PASS: 68 |
| Retained PostgreSQL integration selection | PASS: 5 |
| Retained real Redis/RQ lifecycle selection | PASS |
| Recorded post-remediation focused selection | PASS: 243 |
| Recorded full Python suite | PASS: 5,675 passed, 58 skipped |
| Recorded frontend lint and JavaScript suite | PASS: lint and 745 tests |
| Recorded stub, test-stub, and repaired isolation gates | PASS |
| Local runtime Profile/Preferences read-only smoke | PASS: HTTP 200 |
| Local runtime worker recovery | PASS: affected tree reached 3/3 finished |
| Supplied existing-run delineation acceptance observation | **FAIL: clarified `error` expectation completed under persisted `warn`** |
| Acceptance preference-save/new-run E2E | **BLOCKED / NOT COMPLETED** |
| Forest migration and authenticated canary | **BLOCKED / NOT RUN** |

Independent corroborating checks during this review ran the eight
finding-specific test files through `wctl`; all **151 tests passed**, with no
skip. That selection includes the real PostgreSQL and Redis/RQ suites. The
direct migration-body unit cycle also passed separately: **1 passed**.

The isolated checkpoint results for RQ graph, broad exceptions, diff check,
package docs, and 68 affected WBT/RQ tests are accepted as supplied immutable
gate evidence. The complete Python and frontend results are recorded in the
immutable ExecPlan/tracker and were not rerun by this reviewer.

## Containment, Recovery, and Post-action Controls

- No Forest or production connection was made and no acceptance mutation was
  performed.
- The live job/run facts above were supplied by the parent operator; this
  reviewer performed no follow-up query or mutation against that environment.
- No secret, credential, JWT, cookie, CSRF value, or database password appears
  in the retained evidence reviewed here.
- The PostgreSQL test fixture cleans its users/runs, and the Redis integration
  uses unique queue names with explicit job/queue teardown.
- The retained disposable migration database was dropped after validation.
- The runtime smoke is operational recovery evidence only. It records idle
  verification before coordinated local worker restart, requeues only the
  affected failed job, and reaches a terminal 3/3 tree. It does not substitute
  for the blocked preference-save/new-run acceptance canary.
- The version-skew incident reinforces the reviewed Forest requirement to
  quiesce enqueue, drain, stop bind-mounted consumers before checkout, migrate
  once, verify schema, and restart compatible services together.
- The additive-schema application rollback remains the only reviewed
  nondestructive Forest rollback. An unsupported or ambiguous Alembic
  downgrade must not be improvised during recovery.

## Gate Decision

- **Unresolved High**: 1
- **Unresolved Medium**: 1
- **Unresolved Low**: 0
- **Local acceptance E2E**: remains blocked.
- **Forest preflight/migration/canary**: remains blocked.
- **Release recommendation**: reject and require the existing-run
  authority/snapshot contract correction, the scoped migration evidence
  correction, and a new immutable independent re-review.

No implementation change, Forest action, external message, or break-glass
operation was authorized or performed by this review.
