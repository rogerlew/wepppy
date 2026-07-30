# SURF-14A User-Context Amendment Governance Re-review

## Metadata

- **Reviewer**: independent governance/correctness control agent
- **Date**: 2026-07-30 UTC
- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Starting implementation revision**:
  `b593fb1d8595f6c3c9862ce773def31d372d787c`
- **Review boundary**: frozen working-tree documentation fingerprint listed
  below
- **Runtime, acceptance, Forest, or production mutation**: none

This was a fresh documentation-only re-review after correction of
GOV-CTX-01 and GOV-CTX-02. Historical owner-only and earlier amendment reviews
were treated as evidence, not inherited approval. Runtime source remained
unchanged; no canonical contract, implementation, acceptance state, Forest
state, or production state was modified by this reviewer.

## Verdict

**PASS — APPROVE the governance/correctness side of the user-context
amendment checkpoint for this exact fingerprint.**

**Findings**: 0 High, 0 Medium, 0 Low.

The operator's superseding decision is now represented as an authenticated
viewing-user/initiating-user contract without relying on project ownership to
select account preferences. Existing authorization remains prior to preference
resolution. Non-Auto units remain presentation-only, and account-derived WBT
policy remains job-scoped rather than durable project state.

This approval is deliberately narrow. It does not by itself authorize
implementation, local acceptance mutation, Forest execution, production
execution, destructive migration downgrade, or bypass of any independent
control. The independent operations/security checkpoint review, findings
disposition, and a standalone documentation ancestor remain prerequisites
before implementation may proceed. No break-glass authority was requested or
used.

## Prior Findings Disposition

### GOV-CTX-01 — Closed

The active records now distinguish the accepted original checkpoint from the
pending superseding checkpoint:

- the contract decision has a checked **Original Checkpoint Gate**, explicitly
  superseded for preference lifetime and authority, and a separate
  **User-Context Amendment Checkpoint** whose independent reviews,
  disposition, and standalone ancestor remain unchecked;
- the tracker separately records the completed original gate and the pending
  amendment gate;
- the package labels ADR-0033 as “original decision accepted; user-context
  amendment pending”;
- the ExecPlan says only the project/config baseline may persist; and
- package security language now describes removal of creation-path preference
  propagation with compatibility coverage.

The records no longer reuse the original reviews or ancestor as approval of
the superseding behavior.

### GOV-CTX-02 — Closed

The private snapshot key is now `config_policy`, bound exactly to
`_wbt_boundary_touch_config_behavior` and explicitly never to
`_wbt_boundary_touch_behavior`. The amendment and canonical RQ contract define
the same source/effective relationships and reject Boolean integer fields,
nonpositive actor IDs, schema versions other than integer `1`, missing or
extra keys, unknown enums, and canonical run-ID mismatch.

The regression contract also requires a legacy/superseded-state fixture in
which the two durable fields differ. It must prove exact root metadata,
bounded child arguments, open-polling redaction, correct effective
policy/source, and byte-stable durable fields. There is no remaining choice
between two possible backing fields.

## Governance and Correctness Controls

### Authority, legitimacy, and scope

- The durable amendment quotes the requesting operator's controlling
  user-not-owner and nonmutating-unit decisions and records the actual
  participants. It does not attribute participation or approval to a
  stakeholder who was not present.
- Preference resolution follows ordinary run authorization. The amendment
  does not use a preference, ownership, sharing receipt, or public capability
  to grant new access.
- The route inventory gives every in-scope presentation producer an explicit
  authorization disposition. The debris-flow report's authenticated CAP
  bypass must be repaired before account overlay resolution; Features Export
  remains explicitly excluded as a durable shared-artifact path.
- Forest authority remains limited to the additive migration and disposable
  canary already granted by the operator. Production/wepp1 remains
  unauthorized.

### Identity, privacy, and failure behavior

- Only an absent session `user_id` permits non-account fallback. A present
  malformed, Boolean, zero, negative, missing, or inactive binding fails
  closed after authorization and before project or queue mutation.
- Open `jobstatus` and `jobinfo` exclude the private policy snapshot and
  project generic `auth_actor` as `null` for every job. Protected operations
  surfaces and logs may retain only the already-sanitized internal actor
  object.
- Route, snapshot, and apply failures have fixed public codes/messages and an
  `error_id`; preference/policy infrastructure responses omit `details`.
  Raw failing jobs, descendant cancellation, and aggregate terminal status
  remain exact.

### Persistence, concurrency, and compatibility

- SI/English unit selection uses a request-local presentation view and cannot
  lock, dump, cache-mutate, or write the shared Unitizer. Auto/config preserves
  the project's exact category selections.
- Account WBT choice is resolved synchronously, copied into exact private job
  input, and never written to either durable boundary-policy field. Workers do
  not query account state.
- The complete mutable WBT child operation runs under the directory-root lock.
  Both forced same-run orders define each job's outcome, final readiness and
  raster state, retained diagnostics, unchanged durable fields, and empty
  active/deferred registries.
- Creation, fork, archive/restore, anonymous/public-session, service/MCP, and
  direct/batch compatibility are explicit. Account preference lookup does not
  reenter project creation.

### Migration, deployment, and revocation posture

- The retained single-fixture PostgreSQL transcript includes literal commands
  and outputs for representative schema initialization, both real parent
  revisions, upgrade, explicit-parent downgrade, re-upgrade, application
  assertions, User preservation, cascade behavior, database drop, and absence
  verification. It records the preliminary failed fixture and its cleanup
  without presenting that attempt as the retained proof.
- Forest apply is pinned to one full reviewed release SHA and asserts exact
  `HEAD`. Application rollback is pinned to one full pre-reviewed forward
  revert SHA that must descend from the release and asserts exact `HEAD`.
  References to reviewed old behavior are explicitly constrained by that
  forward-revert target; they do not authorize checkout of an unreviewed
  historical commit.
- Apply and rollback both require enqueue quiescence, queue drain, worker-idle
  evidence, graceful worker stop, and an empty registry before changing the
  bind-mounted tree. The additive table is retained; destructive downgrade
  needs separate reviewed authority.
- Failure leaves affected services stopped. Backup validation, User-count
  preservation, coordinated restart ordering, and post-action review remain
  mandatory.

### Acceptance containment and follow-up review

- Local two-user acceptance uses exact `.invalid` emails that must be absent
  before use, numeric User/User-role receipts, gitignored credentials, one
  exact run and sharing receipt, and receipt-bound compensation with unrelated
  counts unchanged.
- Forest uses the requesting operator plus an existing
  operator-designated active test User. It stops rather than creating or
  altering that account or its roles, records exact preference prestate, and
  restores that state while preserving both Users.
- Pre-acceptance dual review, post-local cleanup review, implementation gates,
  exact Forest preflight, and post-Forest dual audit remain obligations. This
  checkpoint approval cannot be reused for those later reviews.

## Required Next Gates

Before implementation:

1. obtain an independent operations/security PASS on this exact fingerprint;
2. record the combined findings disposition without weakening either review;
3. commit the approved documentation as its own ancestor and record that
   exact revision in the active records.

Before local acceptance or Forest:

1. complete the implementation and all contract-required regression,
   migration, frontend, stub, isolation, RQ graph, broad, and documentation
   gates;
2. obtain the required pre-acceptance independent reviews;
3. retain the receipt-bound local acceptance and cleanup transcript and obtain
   post-acceptance confirmation; and
4. perform Forest only against the exact reviewed release/forward-revert pins,
   then complete the required post-action dual audit.

Any change to the reviewed authority, identity, open-polling redaction,
snapshot schema, persistence lifetime, concurrency ordering, migration graph,
deployment pins, or acceptance account/cleanup scope invalidates this approval
and requires another independent review.

## Review Fingerprint

The review used Git `HEAD`
`b593fb1d8595f6c3c9862ce773def31d372d787c` plus the following working-tree
files. Hashes are SHA-256:

| Reviewed file | SHA-256 |
| --- | --- |
| `package.md` | `0328b47e0e133118d277baa14a293ea69b87a79bc0dea9985fb2147caea22f94` |
| `tracker.md` | `f1c65571986092bcb0d1088f6f69cd88014b3fd092ffc82a0714fdf90da8d608` |
| `prompts/active/user_preferences_wbt_boundary_execplan.md` | `c84dec3659aa100a739fd06cf7df09fbba6a489c014d7dfe672e7d6933556b1a` |
| `artifacts/2026-07-30_contract_decision.md` | `4613c3ce3e8fe20be25ead3b11465b12a857b62979550d57965097bd8273139b` |
| `artifacts/2026-07-30_contract_amendment_delineation_snapshot.md` | `6d55a47ca465fa79e9cd88e573acb3d00bdded36c480c3be5590248f0b54abd8` |
| `artifacts/2026-07-30_local_postgresql_redis_evidence.md` | `8007d895dea4eb188efa73ebdc929bd359c18a655c401653237a05fef35f3176` |
| `artifacts/2026-07-30_local_runtime_smoke.md` | `f9453df44ea285ef895c2b523c25b2e17b1942e1450356c948d2a023514906fa` |
| `docs/adrs/ADR-0033-user-defaults-and-wbt-boundary-policy.md` | `5626021b56cca65209547fa413d27b09ca24e12fac4610d35b72380d0840aa7b` |
| `docs/schemas/rq-response-contract.md` | `bcaf683d89d59a463e35fd2f71e6d29f312e54c1cd8fcea4be30cff5c380780b` |
| `docs/work-packages/20260728_pure_ui_unitizer_preferences_contract/package.md` | `b808898f9d49f8e9117464f026a7a466c787fcf9bf1bb054b05ada092fb8ae0a` |
| `docs/work-packages/20260729_pure_ui_public_creation_cap_contract/package.md` | `304b198c32f70de6883a6474a4a0a00cca0cedd9d886a97173b923d45b230c71` |
| `docs/work-packages/20260729_pure_ui_fork_console_contract/package.md` | `06086cb35a7fa75c47d747b7ce2483d8e094755fa7cf9de773b16cccfb90744b` |
| `wepppy/weppcloud/routes/usersum/weppcloud/user-preferences.md` | `6a9dc68bc2393b6ccc3c615f5d1ed43ab5d2a462653fa4fc4246b1a99fa9e3da` |
| `wepppy/weppcloud/routes/usersum/weppcloud/controls/channel-delineation.md` | `8d980ff207cd0c03730b1f4ed582b825caae09606522ee893b116b4803f3ed18` |
| `PROJECT_TRACKER.md` | `429152ccc9bd8792a94a8fffb301f3cd3849e956bf58e99f46095cdb94ec4a76` |
| `docs/work-packages/20260716_pure_ui_contract_standardization_c/artifacts/child_package_register.md` | `8612e320e025daabb1d3c387472384e0543eba4e4af21b6c4412d392a7ee9ac5` |

The ordered manifest digest is
`73159eb602aae94f72bbe44969bed4b39dee91b118277f196f7f6d7a15021da5`.

## Review Validation

- `wctl doc-lint --path
  docs/work-packages/20260729_user_preferences_wbt_boundary/artifacts/2026-07-30_user_context_checkpoint_governance_review.md`
- `diff -u <review-artifact> <(uk2us <review-artifact>)`
- `git diff --check -- <review-artifact>`

All three review-artifact checks passed.
