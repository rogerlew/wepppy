# Tracker - Account User Preferences and WBT Boundary Policy

## Quick Status

**Timezone**: UTC

**Started**: 2026-07-30 04:10 UTC

**Current phase**: Broad validation and final review

**Last updated**: 2026-07-30 07:15 UTC

**Next milestone**: post-remediation broad gates and independent re-reviews

**Security impact**: `high`

**Dedicated security review**:
`artifacts/2026-07-30_security_review.md`

## Task Board

### In Progress

- [ ] Complete focused and broad validation, final reviews, documentation, and
  local E2E.

### Ready

- [ ] Apply and verify the operator-authorized migration on Forest, then run an
  authenticated new-project canary.

### Blocked

- Forest migration is blocked until implementation, migration tests, full
  validation, and final reviews pass.

### Done

- [x] Mapped current User/Profile, Unitizer, new-project override, WBT edge
  detection, typed error, migration, and contract surfaces
  (2026-07-30 04:10 UTC).
- [x] Recorded the operator's `Stop with an error` decision and Forest
  migration authority (2026-07-30 04:10 UTC).
- [x] Scaffolded SURF-14A package, active ExecPlan, contract decision, ADR, and
  security review artifact (2026-07-30 04:10 UTC).
- [x] Received independent governance and operations/security checkpoint FAIL
  reviews and retained both artifacts (2026-07-30 05:20 UTC).
- [x] Dispositioned authority, owner cross-links, legacy state, exact WBT
  cleanup, identity/ownership, creation inventory, async failure, concurrency,
  dual-head migration, and Forest containment findings in the normative
  contract (2026-07-30 05:30 UTC).
- [x] First re-review closed ten findings and retained GOV-02/07/08, SEC-03,
  and OPS-04; amended the field matrix, Cartesian precedence, canonical RQ
  polling schema, and exact bind-mount-safe Forest commands
  (2026-07-30 06:10 UTC).
- [x] Governance second re-review passed. Operations/security closed SEC-03
  and retained only OPS-04; added executable backup verification, enqueue
  quiesce, worker drain/graceful stop/post-stop registry evidence, and exact
  schema assertions (2026-07-30 06:35 UTC).
- [x] Operations/security final confirmation passed OPS-04; both independent
  checkpoint reviews now pass with no unresolved finding
  (2026-07-30 06:50 UTC).
- [x] Committed the reviewed documentation-only checkpoint as standalone
  ancestor `1b412d61a` (2026-07-30 06:55 UTC).
- [x] Implemented and focused-tested the typed model, merge migration,
  preferences service/page, exact creation precedence, and failure-atomic
  ownership for regular and HUC-fire creation (2026-07-30 07:30 UTC).
- [x] Implemented and focused-tested WBT warn/error behavior, deterministic
  edge diagnostics, readiness cleanup, controlled RQ failure, dependent stop,
  and sanitized aggregate jobinfo (2026-07-30 07:30 UTC).
- [x] Added and validated User Preferences and Channel Delineation Usersum
  guidance and rebuilt the generated search index (2026-07-30 07:30 UTC).
- [x] Passed the complete Python suite (5,643 passed, 58 skipped), frontend
  lint, and all 745 JavaScript tests before final-review remediation
  (2026-07-30 06:05 UTC).
- [x] Retained independent final-review FAIL artifacts and blocked Forest/E2E
  on two governance High/four Medium and four operations/security High/four
  Medium findings (2026-07-30 06:15 UTC).
- [x] Remediated creation disclosure and cleanup confinement/correlation,
  WBT stale readiness and exception identity, controlled RQ retention and
  dependent lifecycle, plus HUC service/MCP compatibility
  (2026-07-30 06:40 UTC).
- [x] Added real PostgreSQL concurrency/identity/ownership tests, disposable
  two-head PostgreSQL migration evidence, persisted NoDb snapshot coverage,
  and real Redis worker/tree/HTTP/retry coverage
  (2026-07-30 06:40 UTC).
- [x] Passed 243 focused tests, the post-remediation full Python suite (5,675
  passed, 58 skipped), frontend lint, 745 JavaScript tests, stubs, test-stub
  completeness, and package documentation lint (2026-07-30 07:10 UTC).
- [x] Repaired and passed the scoped isolation gate, restored the mixed local
  web/worker runtime, verified authenticated Profile/Preferences rendering,
  and recovered the affected RQ tree to 3/3 finished
  (2026-07-30 07:10 UTC).
- [x] Checked implementation commit `e861aae36` in an isolated worktree,
  regenerated its line-only RQ graph metadata, annotated the two displaced
  legacy broad-catch boundaries, and passed the graph, broad-exception, and
  68-test affected WBT/RQ gates (2026-07-30 07:15 UTC).

## Decisions

### 2026-07-30 04:10 UTC: Use typed account persistence

**Decision**: Store one constrained `user_preferences` row per User rather than
cookies, JSON, generic key/value state, or run-scoped NoDb.

**Rationale**: The values are account-scoped, security-sensitive defaults with
small stable enums. Typed columns and database constraints make migration,
validation, audit, and compatibility behavior explicit.

### 2026-07-30 04:10 UTC: Snapshot preferences into new runs

**Decision**: Resolve explicit project input, then account preference, then
configuration before `Ron` initialization and persist the effective run state.

**Rationale**: RQ execution must not depend on live profile state; existing,
shared, and forked projects must remain reproducible.

### 2026-07-30 04:10 UTC: Label failure as Stop with an error

**Decision**: The UI uses `Stop with an error`; the stored token is `error`.

**Rationale**: This describes a controlled typed failure and avoids presenting
an intentional guard as a process crash.

### 2026-07-30 04:10 UTC: Preserve warning compatibility

**Decision**: Account preferences default to `config`; the WBT config option
defaults to `warn`.

**Rationale**: Existing users and configs retain current behavior while a
config or explicit user preference can choose fail-closed handling.

## Risks

| Risk | Severity | Mitigation | Status |
| --- | --- | --- | --- |
| Preference silently changes existing/shared runs | High | Resolve only during new-project initialization; forks copy source | Mitigated and focused-tested |
| Explicit unit selection is overwritten | High | Enforce explicit input > account > config precedence | Mitigated and focused-tested |
| DB/preference lookup failure silently falls back | High | Explicit creation failure and failure-atomic run-directory cleanup | Mitigated and focused-tested |
| Invalid enum bypasses UI | High | Exact route/service enums plus DB check constraints | Mitigated and focused-tested |
| Boundary error leaves stale ready output | High | Invalidate readiness and canonical clipped output before typed failure | Mitigated and focused-tested |
| Migration deploys before compatible code | High | Contract, test, review, and Forest preflight gates | Open |
| Concurrent preference saves lose one field | Medium | Validate complete form, lock existing row, retry first-insert race, and update both fields in one transaction | Mitigated and PostgreSQL-tested |
| Authenticated creation leaves an ownerless/public run | High | User-only subject binding, atomic owner association, exact receipt-bound SQL compensation, and confined filesystem cleanup | Mitigated and PostgreSQL-tested |
| Public job status discloses an internal traceback | High | Sanitize retained RQ state and public tree/HTTP payload; preserve structured correlated diagnostics | Mitigated and real-Redis-tested |
| Dual Alembic heads produce an unsafe Forest rollout | High | Merge revision over both heads, representative PostgreSQL cycle, schema-first coordinated restart | Mitigated locally; Forest pending |

## Verification Checklist

### Contract and review

- [x] Two independent checkpoint reviews pass with findings dispositioned.
- [x] Documentation-only checkpoint is a standalone ancestor.
- [x] ADR-0033 is accepted with complete provenance.
- [ ] Final governance and operations/security reviews pass with no unresolved
  high/medium findings.

### Backend and migration

- [x] Model, constraints, migration upgrade/downgrade/upgrade, missing-row
  compatibility, and concurrent update tests pass.
- [x] GET/POST login, CSRF, exact enum, atomic save, PRG, hostile-value, and
  prefix-aware link tests pass.
- [x] Creation precedence, failure atomicity, anonymous, token identity,
  explicit input, existing run, shared run, and fork tests pass.

### WBT behavior

- [x] Config parser and persisted Watershed enum tests pass.
- [x] Synthetic no-edge, warn, error, invalid-value, actionable message,
  stale-readiness, and deterministic edge-ID tests pass.
- [x] rq-engine response preserves the canonical typed error contract.

### Broad and deployment

- [x] Post-remediation `wctl run-pytest tests --maxfail=1` passes (5,675
  passed, 58 skipped).
- [x] Post-remediation frontend lint and all 745 JavaScript tests pass.
- [x] Stub, test-stub, test-isolation, broad-exception, docs, and RQ graph gates
  pass as applicable.
- [ ] Local stack E2E proves preference save and new-run effective snapshot.
- [ ] Forest preflight records current migration head and database backup
  readiness.
- [ ] Forest migration, schema verification, service restart if required, and
  authenticated canary pass.

## Progress Notes

### 2026-07-30 04:10 UTC: Scaffold

The package was registered as SURF-14A and scoped across the verified Profile,
Unitizer, and Channel Delineation owners. No production implementation or
database migration was performed. The shared worktree already contained
unrelated Pure UI and Command Bar changes; those remain outside this package.

Next, obtain the two required read-only checkpoint reviews, disposition every
finding, and commit only the documentation checkpoint before touching
implementation files.

### 2026-07-30 05:30 UTC: Initial checkpoint review disposition

Both independent reviewers rejected the scaffold revision. Their findings were
accepted and retained under `artifacts/`. The amended contract now records the
operator's execution approval, every affected owner and `Ron(...)` path,
identity and ownership fail-closed rules, legacy field hydration, exact WBT
state/asynchronous transitions, complete-form concurrency, the two-head
Alembic merge, and schema-first Forest containment. No implementation file has
changed. Re-review remains the blocking next step.

### 2026-07-30 06:10 UTC: First re-review

Both reviewers narrowed the remaining checkpoint gaps. The second amendment
round makes the warning/status payload literal, adds the bounded jobinfo schema
to the canonical RQ response contract, factors precedence into a tested
Cartesian product, corrects the DOM-05 field matrix, and stops every
bind-mounted consumer before Forest checkout/migration. Second re-review is
pending; implementation remains untouched and blocked.

### 2026-07-30 06:35 UTC: Second re-review

Governance passed. Operations/security accepted the async RQ contract and
retained only deployment quiescence. The plan now creates and validates a
fresh backup, blocks all enqueue surfaces, proves default/batch queues drained,
stops idle workers gracefully, re-checks registries, and asserts User count
plus all four named constraints before restart. Final OPS-04 confirmation is
pending.

### 2026-07-30 06:40 UTC: Final-review remediation

Both independent final reviews rejected the first implementation. All
reported implementation controls were remediated locally, and durable
PostgreSQL/Redis evidence was added under
`artifacts/2026-07-30_local_postgresql_redis_evidence.md`. The focused
post-remediation selection reached 242 passes with one test-only structured
log field assertion failure; that logging field was added and its focused
rerun passed. Broad gates and immutable-revision re-review remain pending, so
Forest and acceptance E2E remain blocked.
