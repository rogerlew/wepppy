# Delineation Snapshot Checkpoint Operations and Security Review

## Metadata

- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Reviewer**: independent operations/security control agent
- **Review date**: 2026-07-30 UTC
- **Starting implementation revision**:
  `b593fb1d8595f6c3c9862ce773def31d372d787c`
- **Original accepted contract ancestor**:
  `1b412d61ab1173c53c6def06f123d124aaf8bfd1`
- **Review scope**: uncommitted documentation-only delineation-snapshot
  amendment
- **Implementation mutation by this review**: none
- **Forest or production access/mutation by this review**: none

The review inspected only the listed documentation delta and read immutable
`b593fb1d8` source where needed to verify route, token, ownership, RQ, and NoDb
boundary assumptions. Unrelated shared-worktree changes were excluded.

## Reviewed Document Snapshot

The following SHA-256 values identify the exact uncommitted documents reviewed:

| Document | SHA-256 |
| --- | --- |
| `artifacts/2026-07-30_contract_amendment_delineation_snapshot.md` | `cc84c51a470dd20dbbe15b39948e0562445ae9cefea79cbaf6f0e2049b0cfaa5` |
| `artifacts/2026-07-30_contract_decision.md` | `837a17b675bf9d5a007174accbc48f37e32ac50aa9e4cfebf91518a88f432485` |
| `docs/adrs/ADR-0033-user-defaults-and-wbt-boundary-policy.md` | `f38bb017af7c458a4a058acdae3089cf8ab703e9ea1ae58231747b6d7e841a80` |
| `docs/schemas/rq-response-contract.md` | `a22bde010421dee4ea1dd3d0a130767e57b20ffbb1c88e62aff8205924e2b0c0` |
| `package.md` | `fd18b53fdb6a4c5f3d4053df640d40ae5c96a5f905e6d82337c6d3851d46df96` |
| active ExecPlan | `076f43779b3a7e54cf814eb87f7171abaf4ddf83fac462af7a3ea754cf1ebda1` |
| `tracker.md` | `3138bf8ffc25ccfd02c9518d4cb37261607d5e97c686376011568e0987a5b649` |
| `artifacts/2026-07-30_local_postgresql_redis_evidence.md` | `5647050d92f105fa1671baa1ad75dbafacd81c1e9e6b03769d11d4ad9bafec86` |

## Verdict

**FAIL — reject the checkpoint and do not begin implementation.**

The amendment correctly records the operator's clarified observable
requirement from root job `0734dcbc-dd03-4c28-98f4-cb42ea64170c`, but its
identity, owner, session, RQ snapshot, and audit boundaries are not yet precise
enough to implement safely. Two High and five Medium findings remain.

The most material risks are:

- selecting the wrong account on a shared, admin-accessed, multi-associated, or
  session-token run;
- accepting an account-bearing session that has no numeric User binding;
- silently using persisted `warn` after a missing, malformed, or unapplied
  `error` snapshot;
- retaining a session identifier in public job information despite the
  amendment's explicit prohibition; and
- implementing against mutually inconsistent canonical package, ADR, plan, and
  tracker text.

The documentation-only amendment may be revised and re-reviewed. Acceptance
mutation, Forest preflight, Forest migration/canary, and runtime implementation
remain blocked. No break-glass justification exists.

## Finding Summary

| ID | Severity | Finding | Status |
| --- | --- | --- | --- |
| `AMEND-SEC-01` | High | Actor/session and controlling-owner binding are ambiguous | Open |
| `AMEND-SEC-02` | High | RQ snapshot/audit lacks an exact fail-closed and redacted contract | Open |
| `AMEND-OPS-03` | Medium | `config` fallback and nonstandard path matrices are incomplete | Open |
| `AMEND-OPS-04` | Medium | NoDb ordering, retry, and application-rollback containment are incomplete | Open |
| `AMEND-OPS-05` | Medium | Canonical amendment documents contradict one another | Open |
| `AMEND-OPS-06` | Medium | PostgreSQL graph cycle passed, but setup evidence is not fully reproducible | Open |
| `AMEND-OPS-07` | Medium | Regression, acceptance, and Forest-canary plans do not cover the new behavior | Open |

## High Findings

### AMEND-SEC-01 — Actor/session and controlling-owner binding are ambiguous

The amendment consistently says an authorized account-bearing request uses the
active run owner's preference rather than a shared viewer's preference. That is
the correct authority direction, but the controlling identities are not
defined against the actual schema and token contracts.

At `b593fb1d8`:

- `Run.owner_id` is a singular string column;
- `runs_users` is a many-to-many association and may return more than one
  User;
- `authorize_run_access()` treats Admin/Root as authorized without ownership;
- an rq-engine `token_class=session` JWT identifies a session in `sub` and
  `session_id`;
- `user_id` on that session JWT is optional; and
- public-run fallback can mint a valid run-scoped session JWT with no numeric
  User ID.

Evidence:

- `wepppy/weppcloud/app.py`, lines 160-172 and 401-402;
- `wepppy/microservices/rq_engine/auth.py`, lines 125-159 and 262-284; and
- `wepppy/microservices/rq_engine/session_routes.py`, lines 870-968.

The amendment instead uses the undefined phrase `active owner`, combines
`user` and `session` as account-bearing principals, requires a stable numeric
actor User ID, and says run-session identities cannot impersonate an account.
It does not state:

- whether the controlling owner is exclusively `Run.owner_id` or a member
  selected from `runs_users`;
- what happens when `owner_id` is null, nonnumeric, inactive, absent from
  `runs_users`, or conflicts with multiple associations;
- whether an authenticated session JWT must carry a validated numeric
  `user_id`;
- how a public fallback session with no User ID behaves;
- whether a session marker alone is ever sufficient for account resolution;
- how an Admin/Root actor is represented and reauthorized; or
- how owner transfer racing with authorization/preference resolution is made
  deterministic.

Selecting the first associated user or treating a session ID as an account
would cross account boundaries. Treating every session as account-bearing
would also silently break the existing authorized public-session path. This is
High because it can apply another person's safety preference or change
authorization behavior without a ratified rule.

Required closure:

1. Define the authoritative controlling owner field. The recommended rule is
   the exact numeric `Run.owner_id`, validated against one active User and the
   expected run association. Any null, malformed, missing, inactive, or
   inconsistent owner must follow an explicit fail-closed row.
2. Define account-bearing principals exactly:
   - `user` requires a stable numeric User binding under the existing token
     contract;
   - `session` requires a valid run marker **and** a server-issued numeric
     `user_id` claim bound to an active User;
   - `session_id` or `sub` must never be interpreted as a User ID; and
   - a public/anonymous session lacking `user_id` needs an explicit compatibility
     decision rather than falling through the account resolver.
3. Require the resolver to revalidate actor authorization, the controlling
   owner, owner activity, and owner preference in one bounded database context.
   Record the accepted behavior if ownership changes concurrently.
4. State that Admin/Root authorization permits the mutation but never makes the
   administrator's preference controlling.
5. Add exact owner, shared-user, Admin, Root, authenticated session,
   public-session, stale session, owner-transfer, association-mismatch, and
   inactive-owner tests.

### AMEND-SEC-02 — RQ snapshot/audit lacks an exact fail-closed and redacted contract

The amendment lists sensible non-secret primitives and correctly prohibits a
worker-time account lookup. It does not define a canonical snapshot schema or
its failure behavior strongly enough for the safety choice.

Missing normative details include:

- exact metadata/argument key and schema version;
- exact field types and bounds;
- accepted token classes and `source` enum;
- whether `prior_policy` and `effective_policy` are required;
- validation at the route, root, and child boundaries;
- run ID, actor ID, owner ID, and root/child consistency checks;
- behavior when the snapshot is missing, malformed, stale, or altered;
- behavior when the worker cannot persist the effective policy;
- whether a failed snapshot application cancels abstraction and leaves
  readiness absent before any WBT execution; and
- which audit fields are internal-only versus returned by open job polling.

The omission is not theoretical. The amendment says a session identifier is
never recorded, while the existing auth-actor hook stores
`{"token_class": "session", "session_id": ...}` in root job metadata.
`job_info` returns `auth_actor`, and the canonical RQ contract currently
permits that field. The RQ contract amendment changes only the dependent state
from stopped to canceled; it does not define the new WBT snapshot, audit
redaction, or session-actor exception.

Evidence:

- amendment, lines 55-88;
- `docs/schemas/rq-response-contract.md`, Job polling responses and WBT
  controlled failure;
- `wepppy/microservices/rq_engine/auth.py`, lines 125-145;
- `wepppy/rq/auth_actor.py`, lines 127-180; and
- `wepppy/rq/job_info.py`, lines 62-76.

A missing or rejected `error` snapshot must never fall back to persisted
`warn`. Retaining a session ID in open polling also violates the amendment's
own security rule. This is High because it affects both fail-closed execution
and authentication metadata exposure.

Required closure:

1. Add the exact bounded snapshot schema to the applicable canonical RQ
   contract, including a version, key/argument location, types, enums, and
   route/root/child validation.
2. State that an account-bearing job with a missing or invalid snapshot, a
   run/owner mismatch, or a failed locked persistence step fails before WBT,
   cancels abstraction, leaves readiness absent, and surfaces a stable
   sanitized error and correlation ID. No persisted/config fallback is allowed
   after enqueue.
3. Define retry precisely:
   - retry/requeue of the same root or child reuses the immutable snapshot;
   - a new HTTP submission resolves a new snapshot; and
   - no worker retry reads account state.
4. Reconcile `auth_actor` with the no-session-identifier rule. For this path,
   retain only token class plus stable numeric actor User ID, or define a
   separate internal audit field and ensure open jobinfo does not return
   session identifiers.
5. Define structured enqueue, root, child, completion, warning, and failure
   audit events, their correlation keys, and their secret/PII exclusions.
6. Require real Redis tests for stored hashes/results, child arguments,
   retry/requeue, malformed/missing snapshot, persistence failure, open
   jobinfo, and structured logs.

## Medium Findings

### AMEND-OPS-03 — `config` fallback and nonstandard path matrices are incomplete

The amendment says an owner preference of `config` or a missing preference row
uses project configuration. It does not name the authoritative project
configuration source after a previous account-bearing delineation has already
persisted an effective override in `watershed.nodb`.

Without that distinction, a sequence such as:

1. project config is `warn`;
2. owner selects `error` and delineates, persisting `error`;
3. owner changes the account preference to `config`; and
4. owner delineates again

can incorrectly reuse persisted `error` instead of returning to project config
`warn`. The snapshot records the prior persisted policy but not the resolved
project-config value or canonical source used to obtain it.

The matrix also does not fully disposition:

- a valid public-run session JWT with no numeric User;
- account-bearing HTTP submissions in batch or `_base` mode, where the current
  route does not create a root/child RQ tree;
- a public but owned run;
- a legacy run with `owner_id` but no matching association;
- an ownerless public run submitted by user, session, service, or MCP; and
- a fork whose copied associations and singular `owner_id` disagree.

Required closure:

- name the immutable/canonical project-config source used for `config`;
- distinguish project config from the prior persisted effective policy;
- add `warn -> error -> config` and `error -> warn -> config` tests;
- add every public/session, batch/`_base`, legacy, ownerless, and fork
  disposition to the matrix; and
- state which non-RQ path persists an account-bearing batch decision, or state
  explicitly that such submissions remain persisted-state-only.

### AMEND-OPS-04 — NoDb ordering, retry, and application-rollback containment are incomplete

The amendment requires the child to persist the effective policy under the
Watershed lock. It does not carry forward all applicable NoDb/RQ mutation
controls:

- scoped `watershed.nodb` cache invalidation immediately before mutable
  hydration;
- directory-root/archive rejection before cache invalidation;
- distributed NoDb lock acquisition and durable dump before WBT;
- readiness invalidation ordering around the durable policy update;
- behavior on lock contention, stale-write rejection, or post-replace
  durability warning;
- exact root/child retry and requeue ordering; and
- safe rollback while jobs with the new argument/schema may still exist.

`b593fb1d8` already clears the scoped cache before worker hydration and uses
the directory-root and Watershed locks. The amendment must preserve and test
those controls rather than reducing the requirement to the phrase
`canonical Watershed/NoDb lock`.

The Forest runbook safely drains old work before deploying new code, but its
application-rollback text does not require the same enqueue quiescence,
queue/worker drain, and coordinated worker stop before returning to an older
job signature. A canary failure can otherwise leave a new-snapshot job for an
old worker.

Required closure:

- cross-link the RQ-scoped NoDb mutation cache-guard standard;
- specify cache-clear, hydration, lock, persistence, readiness, WBT, and
  terminal-state ordering;
- define fail-closed lock/stale-write/persistence behavior;
- require ordering and cache-scope regression tests; and
- apply the same quiesce/drain/stop compatibility controls to application
  rollback before an older route/worker revision starts.

The durable boundary value itself is compatible with `b593fb1d8`; destructive
database or NoDb rollback is not required. The issue is execution ordering and
mixed-version job containment.

### AMEND-OPS-05 — Canonical amendment documents contradict one another

Several reviewed documents retain the superseded new-run-only rule:

- `package.md`, lines 15-20, says later account changes do not silently change
  an existing project;
- ADR-0033, lines 40-44, says legacy state preserves its compatibility value
  through forks regardless of later account changes;
- the ExecPlan Purpose, lines 10-14, says only new projects snapshot defaults;
- the ExecPlan Decision Log, lines 185-188, still says account preferences apply
  only when creating a new project; and
- the tracker risk at line 151 still calls new-project-only resolution a
  mitigated High control.

Those statements conflict with the new rule that an existing run intentionally
persists the active owner's current boundary choice at its next
account-bearing delineation. ADR-0033 also remains simply `Accepted` and its
provenance describes the original approval without clearly identifying the
pending amendment approval.

The contract-first standard requires every applicable canonical contract to
agree before implementation. A later paragraph does not safely supersede an
unmarked contradictory decision.

Required closure:

- update the package overview and ExecPlan purpose;
- mark the old Decision Log entry as superseded for WBT boundary behavior while
  retaining it for Unitizer behavior;
- correct the tracker risk and verification rows;
- reconcile ADR legacy/fork behavior and status/provenance with the pending
  amendment; and
- search the complete amendment scope for remaining `new-project-only`,
  `stopped`, and incompatible snapshot claims.

### AMEND-OPS-06 — PostgreSQL graph cycle passed, but setup evidence is not fully reproducible

The updated evidence materially closes the prior Alembic topology gap:

- the contract now defines the supported fresh baseline as a newly created
  disposable PostgreSQL database initialized to the representative application
  schema, with `user_preferences` absent and both real parents recorded;
- `flask db upgrade` reaches `c91f6b2a4d7e`;
- explicit `flask db downgrade 7b3c068e7a1d` restores both parent heads;
- re-upgrade returns to the merge head; and
- constraints, missing-row defaults, save/load, cascade, and teardown results
  are recorded.

The explicit-target graph cycle and `canceled` dependent correction are
accepted. The remaining evidence gap is reproducibility. The artifact does not
retain the exact redacted commands used to:

- create the database;
- initialize the representative application schema;
- remove `user_preferences`;
- stamp both parents;
- run the application-context assertions;
- verify User preservation; and
- drop each disposable database.

It also says the disposable database was dropped twice without identifying
which of the two named databases each statement closes.

Required closure:

- retain the exact redacted setup, stamp, graph, assertion, and teardown
  commands with exit results;
- identify both disposable databases and prove both were removed; and
- retain the starting/current revision output around each graph transition.

This remains Medium because the observed graph behavior is credible and the
production rollback remains nondestructive, but the evidence is not yet
independently reproducible.

### AMEND-OPS-07 — Regression, acceptance, and Forest-canary plans do not cover the new behavior

The amendment artifact contains a strong high-level regression list. The active
execution documents do not yet implement that list:

- the ExecPlan Plan of Work has no owner/session snapshot implementation
  milestone;
- its focused command omits the new owner/session, real-route PostgreSQL,
  RQ-snapshot, auth-actor, cache-ordering, and real Redis suites;
- its Validation and Acceptance section still covers only creation identity
  and the original WBT raster behavior;
- the tracker marks the old WBT/RQ tests complete but has no pending checklist
  for the new authority/snapshot matrix;
- local E2E still proves only preference save and a new-run snapshot; and
- the Forest canary still exercises only preference save plus new-project
  snapshotting.

The amendment also says all regression evidence, including local acceptance,
is required before final re-review, while the prior operations gate explicitly
keeps acceptance mutation blocked until final re-review passes. That sequence
must not be loosened implicitly.

Required closure:

1. Add a separate implementation milestone for resolver/authorization,
   snapshot schema, root/child propagation, locked persistence, audit, and
   controlled apply failure.
2. Add exact focused test files/commands for every matrix and failure row,
   including the existing session-contract suites or a reviewed `N/A`.
3. Keep non-mutating tests and final independent re-reviews before acceptance
   mutation.
4. Update local acceptance to:
   - create or select an exactly scoped disposable owned run;
   - persist `warn`;
   - change the owner's account preference to `error` after creation;
   - submit delineation through the reviewed user/session path;
   - prove the root and subcatchment child fail, abstraction is canceled,
     eight edge IDs are bounded/sorted, readiness is absent, and public data is
     sanitized; and
   - restore/delete only the exact preference/run state created for the canary.
5. Extend the Forest canary to the newly reviewed existing-run delineation
   behavior, or explicitly justify why equivalent immutable local acceptance
   plus Forest route/schema smoke is sufficient. Any Forest mutation remains
   gated on new final reviews and preflight.
6. Add post-action verification for audit correlation, queue/registry
   emptiness, service health, canary cleanup, and rollback readiness.

## Accepted Controls

The following amendment controls are directionally correct and may be retained:

- The live discrepancy is correctly classified as an intended behavior change,
  not an implementation-only conformance fix.
- Unit preferences remain creation-only.
- A shared viewer's personal preference does not control another owner's run.
- Service/MCP and non-account worker paths perform no account lookup.
- Account resolution occurs before enqueue and the worker does not query
  mutable profile state.
- The bounded snapshot excludes JWTs, cookies, emails, CSRF values, and
  database credentials.
- Existing successful outputs are not deleted retroactively.
- A later account-bearing delineation is the intended refresh boundary.
- `canceled` is now aligned across the domain contract and canonical RQ
  polling contract and matches the proven RQ 1.16.2 deferred-job cleanup path.
- The explicit Alembic target restores both parents and permits graph
  re-upgrade.
- Forest retains backup validation, enqueue quiescence, queue/worker drain,
  stop-before-checkout, schema-first migration, exact constraint checks,
  coordinated restart, nondestructive application rollback, and separate
  approval for destructive downgrade.
- The amendment remains explicitly blocked on two independent approvals and a
  standalone ancestor before implementation.

These positive controls do not offset the active High identity and snapshot
boundary findings.

## Validation Evidence

| Check | Result |
| --- | --- |
| Current HEAD equals starting implementation `b593fb1d8` | PASS |
| Reviewed document hashes retained above | PASS |
| Scoped documentation diff check | PASS |
| Package Markdown lint before this artifact | PASS: 17 files |
| ADR Markdown lint | PASS |
| Canonical RQ contract Markdown lint | PASS |
| Implementation or regression tests | NOT RUN: documentation checkpoint review |
| PostgreSQL graph-cycle claim | Accepted as observed evidence; reproducibility finding remains |
| Forest/production access | NOT PERFORMED |

No credential, JWT, cookie, CSRF value, session token, database password, or
secret was observed in the reviewed documents. The root job ID and run ID are
operational correlation identifiers supplied by the requesting operator, not
authentication credentials.

## Containment and Gate Decision

- **Unresolved High**: 2
- **Unresolved Medium**: 5
- **Unresolved Low**: 0
- **Checkpoint**: FAIL
- **Runtime implementation**: blocked
- **Acceptance mutation**: blocked
- **Forest preflight/migration/canary**: blocked
- **Production/wepp1**: out of scope and untouched

The safe next action is documentation-only remediation of every finding,
followed by a new independent read-only checkpoint review. Only a dual-approved
and dispositioned standalone ancestor can authorize implementation. Final
implementation review must then verify the exact ancestor, regression
evidence, mixed-version containment, recovery path, and post-action controls.
