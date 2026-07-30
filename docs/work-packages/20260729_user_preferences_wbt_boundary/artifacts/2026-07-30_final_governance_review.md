# Final Governance and Correctness Review

**Review date**: 2026-07-30 UTC

**Reviewer**: Independent governance control agent

**Reviewed contract checkpoint**:
`1b412d61ab1173c53c6def06f123d124aaf8bfd1`

**Implementation basis**: repository HEAD
`18d7b40e38cf4a873f2fe3f20ef6efe0bd8cc6ce` plus the uncommitted
implementation and test worktree inspected through 2026-07-30 06:01 UTC.

## Verdict

**FAIL — REJECT release and Forest rollout approval.**

The implementation does not conform to the ratified WBT readiness and
controlled-failure contracts, and the required durable database, identity,
ownership, migration, and live-RQ evidence is incomplete. The safe
scope-reduction is local remediation, testing, and documentation only. Do not
apply the Forest migration or run the Forest canary on this revision.

**Unresolved findings**: 2 high, 4 medium, 0 low.

## Review Scope

The review inspected the checkpoint-to-current implementation and tests for:

- the account model, merge migration, preference service, Profile link, and
  User Preferences GET/POST contract;
- regular and HUC-fire creation precedence, identity binding, effective NoDb
  snapshotting, ownership, and compensating cleanup;
- persisted WBT configuration, edge detection, retry/readiness invalidation,
  RQ child/dependent behavior, aggregate job information, and public
  redaction;
- Usersum guidance, package/ExecPlan/tracker claims, and recorded validation.

The worktree also contains unrelated changes. Those changes were preserved and
were not treated as package implementation evidence.

## Findings

### GOV-FINAL-01 — High: WBT readiness can expose an in-progress delineation

The ratified contract requires every WBT attempt to clear both completion
timestamps, remove the canonical raster, replace prior edge identifiers, and
make downstream preflight reject derived outputs while either timestamp is
absent
(`artifacts/2026-07-30_contract_decision.md`, lines 170-176).

`WatershedOperationsMixin.build_subcatchments()` clears both timestamps and
removes `subwta.tif`, but it does not clear or replace `_edge_hillslopes` at
attempt entry (`wepppy/nodb/core/watershed_mixins.py`, lines 527-545). An early
WBT failure can therefore retain the prior attempt's diagnostic identifiers.

More critically, the WEPP readiness check accepts a run solely when
`Watershed.has_subcatchments` is true
(`wepppy/microservices/rq_engine/wepp_routes.py`, lines 80-89), and that
property is only an existence check for `subwta.tif`
(`wepppy/nodb/core/watershed.py`, lines 1191-1192). WBT creates that raster
before the build timestamp is written, and abstraction writes its timestamp
later. A concurrent request can therefore pass preflight during a rebuild or
while abstraction remains non-ready, allowing stale derived abstraction state
to be consumed.

Required disposition:

- replace persisted edge identifiers at the start of every
  worker/direct/batch attempt;
- make downstream preflight require both canonical RedisPrep completion
  timestamps, not raster existence alone; and
- add regression tests for an early WBT failure, an in-progress raster,
  stale-derived-output rejection, and successful retry recovery.

### GOV-FINAL-02 — High: controlled failure retains and logs raw tracebacks

The controlled WBT exception handler stores sanitized metadata, removes only
`job.meta["exc_string"]`, and re-raises the exception
(`wepppy/rq/project_rq.py`, lines 965-992). The task is wrapped by
`with_exception_logging`, whose broad catch logs the full exception and writes
`traceback.format_exc()` to the run's `exceptions.log`
(`wepppy/rq/exception_logging.py`, lines 29-38 and 51-70). RQ's worker failure
handler can also retain the re-raised exception in the job traceback field.

Suppressing `exc_info` in `job_info` changes the public rendering but does not
meet the normative requirement that no raw traceback, path, or exception
representation be returned **or retained**, that RQ traceback fields be
sanitized, and that the structured diagnostic log contain no traceback
(`artifacts/2026-07-30_contract_decision.md`, lines 213-220).

Required disposition:

- handle this expected typed failure without the generic traceback-writing
  decorator path;
- sanitize the actual persisted RQ traceback fields, not only the public
  serializer; and
- prove with a real queued job that RQ state, run logs, host structured logs,
  child/root job information, and HTTP payloads contain only the authorized
  code, message, edge IDs, and `error_id`.

### GOV-FINAL-03 — Medium: the implementation created a second incompatible exception type

The existing public
`wepppy.topo.topaz.topaz.WatershedBoundaryTouchesEdgeError` remains exported
from `wepppy.nodb.core` (`wepppy/nodb/core/__init__.py`, lines 6 and 24).
The WBT mixin and RQ worker instead use a newly defined, distinct class in
`wepppy/nodb/core/watershed_errors.py`. The rq-engine watershed route imports
the old public class in its exception boundary
(`wepppy/microservices/rq_engine/watershed_routes.py`, lines 22-28 and
1020-1025).

A runtime identity check confirmed `public_error is rq_error` is false. This
breaks the ratified reuse of `WatershedBoundaryTouchesEdgeError`, fragments the
public exception contract, and makes catches dependent on import path.

Required disposition: define one canonical typed exception, export that same
runtime object from all supported public modules and stubs, update catches, and
add an identity/raise/catch regression test.

### GOV-FINAL-04 — Medium: database and migration evidence does not meet the contract

The concurrency contract requires existing preference rows to be selected for
update, a bounded select-for-update retry for the first-create race, and
deterministic create-race/update-serialization tests
(`artifacts/2026-07-30_contract_decision.md`, lines 225-232).
`save_user_preferences()` locks the parent `User` row and reads
`UserPreferences` with `session.get()` instead
(`wepppy/weppcloud/user_preferences.py`, lines 85-104). This may serialize
application writers, but it is not the ratified locking algorithm and its
unique-insert retry is not exercised.

The only new migration test invokes the revision body directly against
in-memory SQLite
(`tests/weppcloud/test_user_preferences_migration.py`, lines 13-43). It does not
exercise the Alembic graph or disposable PostgreSQL, and it does not prove the
foreign key, cascade, one-row constraint, missing-row service behavior, atomic
save, first-create race, or last-committed update behavior required by the
ExecPlan and contract. No tests call the real `save_user_preferences()` or
`load_user_preferences()` path.

The ExecPlan narrates a local PostgreSQL upgrade and schema introspection, but
there is no durable transcript artifact, and the required fresh/two-head
PostgreSQL upgrade/downgrade/upgrade cycle is not recorded. The tracker's
completed claim at lines 137-138 is therefore unsupported.

Required disposition: conform the implementation to the ratified locking
contract or formally amend and independently review the contract, then add
disposable-PostgreSQL model, cascade, service, concurrency, and actual Alembic
graph tests with a redacted durable transcript.

### GOV-FINAL-05 — Medium: identity, ownership, and persisted-snapshot acceptance is mocked

The route tests replace `resolve_creation_preferences()`,
`register_owned_run()`, and cleanup helpers with fakes. They demonstrate route
orchestration but do not exercise:

- numeric-ID versus exact-`fs_uniquifier` binding;
- unknown, inactive, conflicting email, or missing-subject failure;
- real atomic `Run` plus `runs_users` ownership;
- SQL/filesystem compensation against actual persistence;
- persisted Unitizer and Watershed effective values; or
- the existing/shared/fork non-resolution rules.

No new test calls the real `register_owned_run()` or
`resolve_creation_preferences()` against the account database. This falls
short of the explicit acceptance matrix in
`artifacts/2026-07-30_contract_decision.md`, lines 92-162 and 298-306. The
tracker nevertheless marks token identity, ownership-related failure
atomicity, existing/shared runs, and forks complete at lines 141-142.

Required disposition: add database-backed regular and HUC-fire creation tests
covering the complete identity/operation matrix, real owner association and
compensation, and persisted NoDb effective state. Retain separate unit tests
for pure precedence logic.

### GOV-FINAL-06 — Medium: RQ dependent lifecycle and graph evidence are incomplete

On the controlled failure path, the worker calls
`dependent.set_status(JobStatus.STOPPED)` and `dependent.save()`
(`wepppy/rq/project_rq.py`, lines 975-980). In the installed RQ version,
`Job.set_status()` only writes the job hash; it does not remove the job from
`DeferredJobRegistry` or otherwise perform canonical cancellation/registry
cleanup. The unit test uses fake job and dependent objects, so it cannot prove
the real registry state, terminal tree aggregation, or that abstraction can
never execute.

The contract requires exact endpoint payloads, terminal aggregation, no
abstraction, retry, graph regeneration, and live-tree evidence
(`artifacts/2026-07-30_contract_decision.md`, lines 193-223). No live-tree
artifact exists. The canonical `wctl check-rq-graph` gate also fails with drift
in both `wepppy/rq/job-dependency-graph.static.json` and
`wepppy/rq/job-dependencies-catalog.md`.

Required disposition: use a canonical RQ lifecycle operation that leaves the
dependent terminal and removes stale registry membership, prove the behavior
with real RQ/Redis and HTTP job-status/job-information tests, regenerate both
graph artifacts, pass `wctl check-rq-graph`, and retain the live-tree evidence.

## Validation Evidence

The reviewer ran the following relevant checks:

| Check | Result |
| --- | --- |
| Focused preference, migration, profile, creation, WBT, job-info, and RQ tests | PASS: 294 passed |
| `wctl check-test-stubs` | PASS |
| Stubtest for `wepppy.weppcloud.user_preferences` | PASS |
| Stubtest for `wepppy.nodb.core.watershed` | PASS |
| Package and affected Usersum Markdown lint | PASS |
| In-scope `git diff --check` | PASS |
| `wctl check-rq-graph` | FAIL: both generated graph artifacts drift |
| Changed-file broad-exception gate from the checkpoint | FAIL in the shared worktree; reported additions were outside the reviewed package delta |
| `wctl check-test-isolation` | INCONCLUSIVE: exited zero while reporting one failure for every seed before claiming no isolation issue |

Passing focused tests do not close findings whose missing behavior is mocked or
not asserted. The self-reported full Python and frontend results in the
ExecPlan/tracker have no transcript artifact. Their recorded 07:45 UTC
completion time was also later than both the files' modification time and this
06:01 UTC evidence snapshot, so those prose claims are not accepted as durable
final-review evidence.

## Positive Controls Observed

- The migration is additive, names the four specified constraints, and names
  both preexisting heads.
- The preference page is authenticated, uses the global CSRF boundary, renders
  the exact enum choices, uses PRG on success, and links from Profile.
- The pure precedence implementation preserves explicit unit input over the
  account default and keeps service/MCP creation config-only.
- Regular and HUC-fire routes attempt failure-atomic ownership and directory
  cleanup.
- WBT edge identifiers are sorted and deduplicated after successful edge
  detection, and public job information suppresses controlled-failure
  tracebacks.
- The new Usersum pages are linked and pass the canonical Markdown lint.

These controls are directionally correct but do not outweigh the two active
high-severity contract failures or substitute for the missing integration
evidence.

## Re-review Gate

A new independent final review is required after all six findings are fixed
and the package documents are corrected to distinguish proven checks from
pending checks. Re-review evidence must be tied to an immutable implementation
revision and include:

1. disposable-PostgreSQL migration/model/concurrency transcripts;
2. database-backed identity, ownership, cleanup, and persisted-snapshot tests;
3. WBT stale-state, in-progress-readiness, and retry-recovery tests;
4. a real RQ/Redis child/dependent tree and sanitized-retention transcript;
5. clean graph, stub, isolation, broad-exception, docs, focused, and full-suite
   gates; and
6. a passing independent operations/security review.

Forest authority remains conditional and unexercised. No break-glass
justification exists for bypassing these review gates.
