# Immutable Final Governance and Correctness Re-review

## Metadata

- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Reviewer**: independent governance control agent
- **Date**: 2026-07-30 UTC
- **Ratified contract checkpoint**:
  `1b412d61ab1173c53c6def06f123d124aaf8bfd1`
- **Reviewed implementation checkpoint**:
  `b593fb1d8595f6c3c9862ce773def31d372d787c`
- **Implementation parent**:
  `e861aae36fda0fcf851fc864dcb1e25d9282db77`
- **Prior review**:
  `artifacts/2026-07-30_final_governance_review.md`
- **Forest or production mutation**: none

This review read the immutable Git tree directly. Unrelated dirty-worktree
changes were excluded, and no implementation file was modified.

## Verdict

**FAIL — REJECT release, acceptance E2E mutation, and Forest rollout.**

The two prior High findings and one prior Medium finding are closed. Three
prior Medium findings are only partially remediated: the retained migration
cycle does not satisfy the ratified fresh and graph-level
upgrade/downgrade/upgrade requirement; database-backed creation evidence does
not cross the real regular/HUC route boundary or cover existing/shared/fork
rules; and the public dependent status is `canceled` rather than the
contracted `stopped`.

**Unresolved prior findings**: 0 High, 3 Medium, 0 Low.

The safe scope-reduction remains local contract correction, implementation,
and testing. No break-glass justification exists for bypassing the remaining
contract and review gates.

## Prior Finding Disposition

| Prior finding | Prior severity | Disposition at `b593fb1d8` |
| --- | --- | --- |
| GOV-FINAL-01: WBT readiness can expose an in-progress delineation | High | **Closed** |
| GOV-FINAL-02: controlled failure retains and logs raw tracebacks | High | **Closed** |
| GOV-FINAL-03: incompatible duplicate exception type | Medium | **Closed** |
| GOV-FINAL-04: database and migration evidence incomplete | Medium | **Open — partially remediated** |
| GOV-FINAL-05: identity, ownership, and persisted-snapshot acceptance mocked | Medium | **Open — partially remediated** |
| GOV-FINAL-06: RQ dependent lifecycle and graph evidence incomplete | Medium | **Open — partially remediated** |

## Closed Findings

### GOV-FINAL-01 — Closed: WBT invalidation and downstream readiness

The WBT attempt now persists an empty `_edge_hillslopes` set before invoking
WBT delineation
(`wepppy/nodb/core/watershed_mixins.py`, lines 527-547). The same entrypoint
clears both RedisPrep timestamps and removes the prior canonical
`subwta.tif`.

WEPP preflight now requires:

1. canonical `subwta.tif` presence;
2. the `build_subcatchments` timestamp; and
3. the `abstract_watershed` timestamp.

If either timestamp is absent, the route returns the existing 409
not-ready response
(`wepppy/microservices/rq_engine/wepp_routes.py`, lines 80-105).

The exact tree includes regression tests for a pre-detection failure with
stale edge IDs and for every missing-timestamp combination
(`tests/nodb/test_wbt_boundary_touch_behavior.py`, lines 189-212;
`tests/microservices/test_rq_engine_wepp_routes.py`, lines 154-180).
The isolated affected WBT/RQ selection passed 68 tests.

This closes both the stale diagnostic state and the in-progress raster
consumption paths from the prior High finding.

### GOV-FINAL-02 — Closed: retained controlled-failure data is sanitized

`build_subcatchments_rq()` is no longer wrapped by the generic
`with_exception_logging` decorator. Its typed catch records only the
authorized error payload and correlation fields, emits a traceback-free
structured log, cancels dependent abstraction, and re-raises for RQ failure
state (`wepppy/rq/project_rq.py`, lines 924-1022).

`WepppyRqWorker` detects the structured controlled error in both
`handle_exception()` and `handle_job_failure()`. It passes only the actionable
message to the RQ superclass and overwrites `meta["exc_string"]` with that
message (`wepppy/rq/rq_worker.py`, lines 218-294). It does not call the generic
traceback formatting branch for this failure.

The retained real-Redis evidence records passing tests using an inline
`WepppyRqWorker`. The integration assertions inspect the stored job
`exc_info`, metadata, failed registry, root/child serialization, real
`/api/jobinfo/<id>` response, and structured log. They reject `Traceback` and
the source path
(`tests/rq/test_wbt_controlled_failure_integration.py`, lines 100-205).

The prior raw-retention path is therefore closed.

### GOV-FINAL-03 — Closed: exception identity is canonical

The canonical class and message now live with the existing TOPAZ type
(`wepppy/topo/topaz/topaz.py`, lines 175-198).
`wepppy.nodb.core.watershed_errors` reexports that object instead of defining
a second class, and both `wepppy.nodb.core` and Watershed worker imports reach
the same runtime object.

The identity regression test proves the public core, TOPAZ, and Watershed
imports are identical and that an exception raised through one path is caught
through another
(`tests/nodb/test_wbt_boundary_touch_behavior.py`, lines 215-223).

## Unresolved Medium Findings

### GOV-FINAL-04 — Open: PostgreSQL service proof is strong, but the ratified migration cycle is incomplete

The service/concurrency portion is remediated:

- existing `UserPreferences` rows are selected with `FOR UPDATE`;
- the complete form is committed atomically;
- a unique-insert loser performs one bounded retry; and
- five PostgreSQL integration tests prove constraints, cascade, concurrent
  first saves, serialized existing-row updates, identity binding, ownership,
  exact-receipt deletion, and collision preservation.

Evidence:

- `wepppy/weppcloud/user_preferences.py`, lines 88-127;
- `tests/weppcloud/test_user_preferences_postgres.py`, lines 74-308; and
- `artifacts/2026-07-30_local_postgresql_redis_evidence.md`.

The migration portion remains below the ratified requirement. The contract
requires validation of a fresh upgrade and a database at both heads through
upgrade/downgrade/upgrade
(`artifacts/2026-07-30_contract_decision.md`, lines 247-251 and 298-301).
The retained evidence instead:

- creates a representative application schema and stamps both parents;
- performs a graph-level upgrade to `c91f6b2a4d7e`;
- calls the revision's `downgrade()` and `upgrade()` bodies directly through
  Alembic `Operations`; and
- records that graph-level `flask db downgrade -- -1` failed with
  `Ambiguous walk`.

That is useful PostgreSQL DDL evidence, but a direct revision-body call is not
the contracted Alembic graph downgrade, and the representative stamped schema
is not the separately required fresh-upgrade path. The authoritative contract
was not amended after this limitation was discovered.

Required closure:

- retain a reproducible PostgreSQL transcript for a supported explicit-target
  graph upgrade/downgrade/upgrade and the required fresh path; or
- amend the authoritative migration acceptance contract with the precise
  repository-history limitation, replacement evidence, rollback posture, and
  rationale, then obtain independent checkpoint approval for that change.

Tracker and ExecPlan completion claims must match whichever reviewed contract
is retained.

### GOV-FINAL-05 — Open: the components are tested, but the real creation boundary and compatibility rows are not

The checkpoint materially improves the evidence:

- PostgreSQL tests exercise the real numeric-ID and exact-`fs_uniquifier`
  resolver, negative identities, ownership association, receipt-bound cleanup,
  and collision preservation;
- route tests cover regular/HUC precedence, failure branches, correlation, and
  service/MCP HUC behavior; and
- a real `Ron` test proves effective Unitizer and Watershed values are
  persisted.

However, the regular and HUC route tests still replace
`resolve_creation_preferences()` and `register_owned_run()` with fakes. The
PostgreSQL tests call those services separately rather than through either
production route. No package test proves the accepted existing/shared/fork
rows; repository search finds those requirements in the contract and tracker
but not in SURF-14A regression tests.

This does not meet the original disposition requiring database-backed regular
and HUC creation coverage of the complete identity/operation matrix, nor the
ratified regression requirement for existing, shared, and fork behavior
(`artifacts/2026-07-30_contract_decision.md`, lines 129-162 and 298-306).
The pending acceptance E2E is not a substitute because final review is its
authorization gate.

Required closure:

- add database-backed TestClient coverage that crosses both the regular and
  HUC production routes with real preference resolution and ownership;
- assert persisted Unitizer/Watershed state and exact SQL/filesystem
  compensation through those boundaries; and
- add explicit existing-run, shared-viewer, and fork/archive-copy regression
  cases proving account preferences are not re-resolved.

If those rows are intentionally removed from acceptance, amend and
independently approve the authoritative contract before re-review.

### GOV-FINAL-06 — Open: shared-state cleanup is proven, but the observable status violates the contract

The lifecycle and gate portions are remediated:

- `_cancel_deferred_job()` removes the DeferredJobRegistry entry, detaches the
  parent/dependency sets, deletes the dependency key, and invokes RQ
  cancellation in one Redis pipeline
  (`wepppy/rq/project_rq.py`, lines 197-213);
- real-Redis tests prove empty deferred membership, detached dependency sets,
  non-execution, terminal root failure, sanitized HTTP data, and successful
  subsequent child execution; and
- the isolated `b593fb1d8` gates record RQ graph PASS and 68 affected WBT/RQ
  tests passing.

The implementation deliberately produces `canceled`, and its integration test
asserts `canceled` in the job and public root payload
(`tests/rq/test_wbt_controlled_failure_integration.py`, lines 66-90 and
169-187). The ratified contract requires the dependent abstraction child to
become `stopped`
(`artifacts/2026-07-30_contract_decision.md`, lines 193-195).
No authoritative amendment permits the changed public status.

Required closure:

- implement a supported, registry-clean terminal transition whose observable
  status remains the contracted `stopped`; or
- amend the canonical RQ/status contract and this package to authorize
  `canceled`, document downstream/UI/operator compatibility, and independently
  review that public contract change.

The real-Redis lifecycle evidence can be retained after the status contract is
resolved.

## Validation and Evidence Assessment

The following evidence is accepted as tied to the immutable implementation
checkpoint:

| Gate or evidence | Result |
| --- | --- |
| Checkpoint object and exact parent | PASS |
| Isolated RQ dependency graph gate | PASS |
| Isolated changed-file broad-exception gate | PASS: delta 0 |
| Isolated implementation diff check | PASS: clean |
| Package documentation lint before this artifact | PASS: 14 of 14 |
| Isolated affected WBT/RQ tests | PASS: 68 |
| PostgreSQL preference/identity/ownership integration tests | PASS: 5 |
| Real Redis/RQ controlled-failure integration selection | PASS |
| Post-remediation focused selection recorded in the ExecPlan | PASS: 243 |
| Full Python suite recorded in the ExecPlan | PASS: 5,675 passed, 58 skipped |
| Frontend lint and tests recorded in the ExecPlan | PASS: lint; 745 tests |
| Stub, test-stub, and repaired isolation gates recorded in the ExecPlan | PASS |
| Runtime Profile and Preferences read-only smoke | PASS: HTTP 200 |
| Acceptance preference-save/new-run E2E | **BLOCKED / NOT RUN** |
| Forest migration and authenticated canary | **BLOCKED / NOT RUN** |

The isolated gate repairs in `b593fb1d8` update line metadata and annotate two
legacy broad-exception boundaries without changing the reviewed runtime
behavior. The previously stale graph and shared-worktree broad-exception
failures from the original review are closed.

The local runtime artifact proves route-map synchronization and worker
recovery, but explicitly labels itself operational smoke. It does not close
the missing database-backed creation-route evidence.

## Re-review Gate

A replacement immutable implementation checkpoint and new independent
governance re-review are required after GOV-FINAL-04, GOV-FINAL-05, and
GOV-FINAL-06 are closed. The re-review submission must contain:

1. the unchanged ratified contract plus conforming evidence, or independently
   approved amendments for every intentional deviation;
2. a durable PostgreSQL migration transcript matching the reviewed migration
   acceptance contract;
3. database-backed regular/HUC route tests and explicit
   existing/shared/fork compatibility tests;
4. an exact RQ dependent status that matches the authoritative public
   contract;
5. clean isolated graph, broad-exception, diff, docs, focused, full Python,
   frontend, stub, and isolation gates; and
6. a passing independent operations/security re-review of the same immutable
   checkpoint.

Acceptance E2E and Forest authority remain blocked. The existing Forest
authority is conditional, does not extend to production/wepp1, and is not a
waiver of these controls.
