# User-Context Checkpoint Operations and Security Review

## Metadata

- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Reviewer**: independent operations/security control agent
- **Review date**: 2026-07-30 UTC
- **Starting implementation revision**:
  `b593fb1d8595f6c3c9862ce773def31d372d787c`
- **Original accepted contract ancestor**:
  `1b412d61ab1173c53c6def06f123d124aaf8bfd1`
- **Review boundary**: superseding documentation-only authenticated-user
  context amendment
- **Implementation mutation by this review**: none
- **Local, Forest, or production mutation by this review**: none

The discarded owner-only interpretation and its provisional re-review were not
used as authority. This review starts from the operator's superseding decision:
both preferences follow the authenticated viewing or initiating user, not
`Run.owner_id`; non-Auto units are request-local presentation; and Warn/Stop is
submission input rather than durable account-derived project policy.

## Verdict

**PASS — approve the user-context documentation checkpoint for standalone
ancestor creation.**

- **Unresolved High**: 0
- **Unresolved Medium**: 0
- **Unresolved Low**: 0
- **Decision**: approve the documentation contract

This is not approval to mutate the local acceptance environment, Forest, or
production. Runtime implementation remains gated on both independent
checkpoint approvals and a committed standalone amendment ancestor. Local
acceptance, Forest migration/canary, and any production action retain their
separate implementation, test, review, preflight, and operator gates.

## Findings

No unresolved operations or security finding remains in the reviewed
documentation snapshot.

## Control Assessment

### Identity, authorization, and cross-user isolation

**PASS.**

- Existing view or mutation authorization occurs before preference lookup.
- A user token, cookie-authenticated request, or account-bearing run session
  binds to one active positive numeric User.
- A present malformed, Boolean, zero, negative, missing-User, or inactive
  session `user_id` fails closed; only an absent claim makes the session
  non-account-bearing.
- Anonymous/CAP, public session without a User, service/MCP, direct worker, and
  batch paths use project/config state without an account lookup.
- Shared and administrator users use their own preference only after ordinary
  run authorization. Owner and `runs_users` association do not select the
  preference account.
- Preference save and resolution take the same User-row lock, producing one
  coherent old-or-new result; both race orders are required evidence.

### Unitizer presentation and project mutation containment

**PASS.**

- SI/English is an immutable request-local adapter or detached copy.
- The overlay cannot call Unitizer persistence, acquire its persistence lock,
  mutate the shared cached instance, or write `unitizer.nodb`.
- Auto exposes the exact persisted mixed project Unitizer map.
- Project creation and the explicit Unitizer POST mutation remain independent
  durable project operations. Account units do not parameterize either.
- The finite adoption inventory covers run/report producers, GET conversion
  endpoints, and browser initialization.
- The debris-flow report must add ordinary run authorization before adopting
  an account overlay while retaining CAP for authorized anonymous public-run
  viewers.
- The project-fingerprinted feature-export Unitizer uses and `ui_showcase`
  stub are explicitly dispositioned outside the account presentation overlay.
- SHR-05, SURF-01, and SURF-04 preserve project mutation, creation, and fork
  copy semantics.

### WBT snapshot, no-write boundary, and failure containment

**PASS.**

- The route resolves the initiating active User and validates the immutable
  snapshot before any NoDb, RedisPrep, readiness, job-ID, or queue mutation.
- Auto uses the exact immutable
  `_wbt_boundary_touch_config_behavior`; a legacy missing baseline may persist
  only the validated configuration value under the Watershed lock.
- The account-derived effective choice is an in-memory execution view and
  cannot replace `_wbt_boundary_touch_behavior` or the configuration baseline.
- Root and child metadata, bounded arguments, run ID, actor class/User,
  `config_policy`, effective policy, and source have exact schemas and
  consistency rules. Workers never query account state.
- Retry keeps the original snapshot; a new submission resolves the current
  initiating-user preference.
- Snapshot-invalid and apply-failed paths have exact sanitized codes/messages,
  absent public `details`, correlated `error_id`, failed raw jobs, canceled
  deferred abstraction, and terminal failed aggregation.
- The edge-policy error preserves deterministic diagnostics while removing
  canonical clipped output and readiness; warn preserves normal success.

### Open polling and operational diagnostics

**PASS.**

- Open `jobstatus` and `jobinfo` expose neither the private policy snapshot nor
  actor identifiers.
- Generic open `auth_actor` is projected as `null`, closing exposure of
  numeric User, session, and service/MCP identifiers through adjacent
  metadata.
- Sanitized internal actor metadata remains confined to protected Admin/Root
  operations surfaces and server logs.
- Logs may carry bounded correlation and numeric actor/run/job facts but may
  not contain JWTs, cookies, session identifiers, email, CSRF tokens, or
  database credentials.
- Exact open-polling and real-Redis root/child/redaction tests are required
  before release.

### Cache, lock, readiness, and same-run concurrency

**PASS.**

- Directory preflight, exact cache clear, durable hydration, snapshot
  validation, nonpersistent execution-view construction, readiness
  invalidation, and delineation execute within the existing watershed
  directory-root lock.
- Invalid snapshot, cache, lock, stale state, or execution-view failure cannot
  clear readiness or begin WBT.
- Both forced same-run orders are specified:
  - A/error then B/warn ends with B's successful raster/readiness;
  - B/warn then A/error ends without canonical raster/readiness and retains
    A's diagnostics.
- Each job has its own snapshot and terminal result, both durable policy fields
  remain byte-stable, and active/deferred registries must be empty after each
  order.
- The cache-clear placement matches the scoped NoDb cache-guard standard.

### Migration execution trace and teardown

**PASS.**

The retained `surf14a_graph_cycle_0910` evidence contains:

- the literal executed disposable-database, representative-schema,
  both-parent, upgrade, current, application-assertion, explicit downgrade,
  re-upgrade, teardown, and absence-check commands;
- zero exit status and output from the same fixture;
- both parent rows before upgrade and after downgrade;
- the exact merge head after both upgrades;
- all four named constraints, missing-row defaults, saves, User preservation,
  cascade behavior, and zero remaining preference rows; and
- successful `dropdb` followed by a zero-count PostgreSQL catalog query for the
  exact disposable database.

The transcript records the preliminary interrupted fixture and its cleanup.
No application, Forest, or production database was used.

### Mixed-version apply, recovery, and rollback

**PASS.**

- Apply creates and validates a fresh custom-format backup before code/schema
  mutation.
- Enqueue surfaces stop first; both queues drain; workers must all be idle
  before graceful stop; post-stop queue and worker registries must be empty.
- Release and rollback variables must resolve to exact commits, and the
  pre-reviewed forward revert must descend from the release.
- Fast-forward apply must end at the exact reviewed release SHA before
  migration.
- All changed long-lived consumers remain stopped during migration and restart
  together before the scheduler.
- Application rollback repeats quiescence, drain, idle, stop, and
  zero-registry checks; fast-forwards to the exact pre-reviewed revert; asserts
  `HEAD`; and preserves the additive table.
- Destructive downgrade or restore requires separate operator authority.
- Mismatch, failed backup/schema/constraint/User-count check, unhealthy
  service, or failed canary aborts the rollout.

### Local and Forest two-user acceptance

**PASS.**

- Local acceptance uses two exact, collision-checked, disposable local-only
  accounts, non-secret User/role receipts, one run, and one sharing receipt.
- Local credentials remain in a gitignored secret boundary.
- Cleanup removes only receipt-bound local accounts, roles, preferences, run,
  association, and credentials, then proves their absence and unchanged
  unrelated counts.
- Forest uses the requesting operator plus one existing
  operator-designated active account; it may not create a User or alter roles.
- Forest preflight records both numeric IDs, both exact prior preference rows,
  one run, and one association.
- Forest cleanup restores preexisting preference rows exactly, deletes only a
  row proven absent before the canary, removes only the canary run/association,
  preserves both Users, and verifies no unrelated row changed.
- Both environments require two-user presentation, distinct error/warn and
  Auto/config behavior on one unchanged project, private redaction,
  byte/hash-stable Unitizer and durable WBT policies, service/queue health,
  cleanup, and post-action dual review.

## Reviewed Working-Tree Fingerprint

`HEAD` was
`b593fb1d8595f6c3c9862ce773def31d372d787c`. The reviewed documents were
uncommitted working-tree state; SHA-256 values below identify the exact
snapshot:

| Document | SHA-256 |
| --- | --- |
| user-context amendment | `6d55a47ca465fa79e9cd88e573acb3d00bdded36c480c3be5590248f0b54abd8` |
| `package.md` | `0328b47e0e133118d277baa14a293ea69b87a79bc0dea9985fb2147caea22f94` |
| contract decision | `4613c3ce598f1c30a12108f904076a2e3ad3b04b698624187defb952857e47d0` |
| active ExecPlan | `c84dec3659aa100a739fd06cf7df09fbba6a489c014d7dfe672e7d6933556b1a` |
| `tracker.md` | `f1c65571986092bcb0d1088f6f69cd88014b3fd092ffc82a0714fdf90da8d608` |
| ADR-0033 | `5626021b56cca65209547fa413d27b09ca24e12fac4610d35b72380d0840aa7b` |
| RQ response contract | `bcaf683d89d59a463e35fd2f71e6d29f312e54c1cd8fcea4be30cff5c380780b` |
| SHR-05 package | `b808898f9d49f8e9117464f026a7a466c787fcf9bf1bb054b05ada092fb8ae0a` |
| SURF-01 package | `304b198c32f70de6883a6474a4a0a00cca0cedd9d886a97173b923d45b230c71` |
| SURF-04 package | `06086cb35a7fa75c47d747b7ce2483d8e094755fa7cf9de773b16cccfb90744b` |
| Channel Delineation Usersum | `8d980ff207cd0c03730b1f4ed582b825caae09606522ee893b116b4803f3ed18` |
| User Preferences Usersum | `6a9dc68bc2393b6ccc3c615f5d1ed43ab5d2a462653fa4fc4246b1a99fa9e3da` |
| local PostgreSQL/Redis evidence | `8007d895dea4eb188efa73ebdc929bd359c18a655c401653237a05fef35f3176` |
| local runtime smoke | `f9453df44ea285ef895c2b523c25b2e17b1942e1450356c948d2a023514906fa` |
| RQ-scoped NoDb cache standard | `22057d1908a4c71657c161bcec6de5ccfc358e68000130defa7faefc27814e0a` |
| `PROJECT_TRACKER.md` | `429152ccc9bd8792a94a8fffb301f3cd3849e956bf58e99f46095cdb94ec4a76` |
| Pure UI child-package register | `8612e320e025daabb1d3c387472384e0543eba4e4af21b6c4412d392a7ee9ac5` |

Read-only source evidence used to verify the authorization and current
open-polling implementation boundary:

| Source | SHA-256 |
| --- | --- |
| `wepppy/microservices/rq_engine/auth.py` | `8a7996e49aec6a946c710040463baa75a9764a00d482d37509812e72fa778b12` |
| `wepppy/rq/job_info.py` | `b533102059150a8f321e1e441e7d97838e6ac633b89bead857e6dbe4df27a67f` |
| debris-flow route | `32e2c4dfae25ed5e5d46e2f0d36d925d285078b2bd4b9b0d92625498fb50f9bb` |
| CAP guard | `e3b5a9633e14120f551b4baa0fd533e7a12141b2604b7083f5ce439c7dd7e8d4` |

Those source hashes describe implementation work still required by the
approved amendment. No source file was changed by this review.

## Validation Evidence

| Check | Result |
| --- | --- |
| Review artifact Markdown lint | PASS |
| Review artifact `uk2us` preview | PASS: no change |
| Review artifact `git diff --check` | PASS |
| Canonical document lint | PASS |
| Canonical document `uk2us` preview | PASS |
| Canonical scoped `git diff --check` | PASS |
| Production Unitizer call-site inventory | PASS: adoption set, exclusions, and debris authorization are dispositioned |
| Runtime implementation/regression tests | NOT RUN: documentation checkpoint |
| Local acceptance | NOT PERFORMED |
| Forest/production access | NOT PERFORMED |

No credential, JWT, cookie, CSRF token, database password, or secret was
observed in the reviewed documents.

## Gate Decision

- **Documentation checkpoint**: approved
- **Standalone amendment ancestor**: required next
- **Runtime user-context implementation**: not yet authorized by this review
  alone
- **Local acceptance mutation**: not yet authorized
- **Forest preflight/migration/canary**: not yet authorized
- **Production/wepp1**: unauthorized and untouched

After the independent governance review also passes, the safe next action is a
standalone documentation commit containing the exact reviewed amendment
snapshot. Runtime work may begin only from that recorded ancestor and remains
subject to the package's implementation and validation gates.
