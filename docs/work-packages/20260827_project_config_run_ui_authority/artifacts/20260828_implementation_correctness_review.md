# WP12D Writer Implementation Correctness Review

**Amendment**: `PC-24/WP12D-20260827-3`
**Review status**: READY
**Review type**: fresh independent post-remediation implementation review
**Reviewer**: independent `implementation_correctness_review` agent
**Review completed**: 2026-08-28 UTC
**Reader-floor base**: `80f4810b7be59d90a64b4771f587eb360987a820`
**Candidate worktree HEAD**: `5eb451a7640fa3148a8872dd74f3756d8c88e7ce`

The review object is the exact uncommitted WP12D writer candidate over the
reader floor at review completion. It excludes only the unrelated dirty paths
recorded in the tracker and validation-generated code-quality reports.

## Verdict

READY for exact-host Forest writer acceptance. No unresolved in-scope
correctness findings remain: High 0; Medium 0; Low 0.

This disposition does not authorize production. Production remains reserved
to the parent WP12 promotion gate after WP12D Forest acceptance.

## Canonical Basis and Boundary

The candidate was reviewed against:

- `docs/schemas/project-owned-config-contract.md`, including the schema-v3
  authority, exact-current, update, atomicity, recovery, diagnostics, and
  evidence requirements;
- `20260827_contract_decision.md`, amendment
  `PC-24/WP12D-20260827-3`;
- `20260827_surface_matrix.md`; and
- the active WP12D ExecPlan and tracker.

Every in-scope implementation change remains within the ratified source and
consumer list. `project_config_capabilities.py` composes frozen stored
authority with the deliberately bounded live legacy authority; it does not
broaden authorization or mutation. Stored schema-v2/schema-v3 reads remain
independent of live Builder-registry drift. The WEPP model presentation path
retains its stored-only and historical compatibility policy, while the live
legacy expansion remains confined to the ratified landuse, soil, and climate
consumers. The Config Builder/Interfaces navigation and feature-registry
ownership non-change assertions remain intact.

## Findings and Disposition

The implementation review initially found fail-closed and parity gaps in the
candidate. The reviewed candidate closes all of them:

- durable preview, manifest, amendment, result, and journal shapes are exact;
  canonical digests, amendment sequence, config/manifest congruence, and
  recovery commit points are revalidated before writes;
- capability and combined refresh preserve every selection-bearing runtime
  value, require the exact preview-bound acknowledgment, resolve application
  revision once, and fail before reservation on stale or malformed state;
- stored authority supplies canonical runtime locale tokens to the scoped
  Australia/Europe hot paths even when flattened `general.locales` is
  incongruent, while schema-v1/no-capability compatibility remains unchanged;
- landuse, soil, and climate presentation, RQ discovery, Flask/RQ mutation,
  operation documents, pipeline, and readiness use the same resolved graph;
- outside-axis current datasets and methods remain visible exactly once as
  disabled values and may be resubmitted unchanged, while different
  unsupported values fail before controller mutation, timestamps, files, or
  enqueue;
- landuse and climate dataset/method aliases must agree, paired selections are
  validated together, and changed selections persist only after validation;
- invalid locale and unavailable-registry responses preserve auth precedence
  and expose diagnostic `details`, `error_id`, and `Retry-After: 5` where
  required; and
- browser terminal success validates the exact RQ result, distinguishes normal
  and recovered commits, reports indeterminate malformed/unavailable outcomes,
  inserts diagnostics through `textContent`, and resets acknowledgment state.

## Final Security-Closure Delta Recheck

The independent reviewer rechecked the exact current candidate after the final
security closures. The recheck found one Medium mutable-preview defect, which
is closed in the reviewed candidate. No delta correctness findings remain:
High 0; Medium 0; Low 0.

`project_config_update.js` now captures an immutable apply-time
`preview_id`/prior-digest/resulting-digest snapshot before asynchronous work.
Recursive polling, terminal success, failure reconciliation, and immediate
recovered HTTP success all use that snapshot rather than mutable visible
preview state. A pending-job regression replaces visible preview B while job A
is unresolved and proves job A is evaluated only against snapshot A. Matching
normal/recovered results succeed; malformed, unavailable, or mismatched results
remain indeterminate without hiding the update control.

The Flask climate dataset/mode boundary now repeats capability authorization
inside one NoDb lock, snapshots both fields after lock acquisition, validates
the runtime mode constraints, and persists the pair in one dump. If the second
field assignment fails, both fields are restored before the lock unwinds. The
concurrent fault regression proves rollback restores the pair current at lock
acquisition rather than a stale pre-lock snapshot.

The reviewer reran 32 climate route tests and 19 `project_config_update` Jest
tests for this delta; all passed. Frontend ESLint also passed.

## Forest Fresh-Worker Import Delta Recheck

Forest acceptance exposed a circular import before the RQ task could execute:
the worker module imported rq-engine authorization at module load while
rq-engine package initialization imported the worker route. The failed attempt
did not change config or manifest bytes, and its reservation was removed by an
exact compare-and-delete.

The reviewed worker now keeps a same-name lazy authorization wrapper. A fresh
RQ process can import the task without initializing rq-engine routes; the
fully loaded task imports and executes canonical mutation authorization before
any project update. The `finally` boundary now uses one single-key Redis Lua
operation to compare the stored reservation with the terminating job ID and
delete only on equality. TTL expiry followed by a replacement reservation
therefore cannot be clobbered by a split read/delete race. This change is
confined to the ratified worker module and does not alter task arguments, queue
topology, authorization semantics, or update persistence.

A real fresh-interpreter subprocess regression resolves the task through
`rq.utils.import_attribute`, preventing the already-imported test process from
masking the cycle. The package also records a successful live fresh rq-worker
import. The independent reviewer reran the worker and update-route suites:
20 tests passed, including authorization-loss/no-mutation, matching
reservation deletion, and preservation of an atomically replaced reservation.
No delta correctness findings remain: High 0; Medium 0; Low 0.

## Forest User-Identity Handoff Delta Recheck

Forest acceptance exposed an identity handoff defect in the browser-issued
user-token path: Flask-Login may use an intentionally opaque security subject,
while the same signed token carries the canonical positive numeric `user_id`.
The route accepted the verified token, but `_sanitize_auth_actor` considered
only the opaque `sub`, omitted the worker actor, and therefore left the worker
without the owner identity needed for its independent mutation authorization.

The exact two-file delta over `326f2138c` now prefers the parsed signed
`user_id` and falls back to a numeric `sub`. The actor remains deliberately
minimal: it carries the user ID and only normalized Admin/Root roles;
PowerUser and other roles are not promoted. Numeric-sub compatibility remains
intact, and malformed identities still produce no actor. The downstream
worker continues to reauthorize the retained identity against current run
ownership or Admin/Root before mutation, so this repairs identity transport
without changing the authorization policy.

The added regression covers an opaque `sub`, numeric `user_id`, and mixed
Admin/PowerUser roles, proving both numeric identity retention and privileged
role filtering. The independent reviewer reran the exact auth, browser-token,
project-update route, and update-worker suite: 116 tests passed. `git diff
--check` also passed for the two-file delta. No delta correctness findings
remain: High 0; Medium 0; Low 0.

## Forest Provenance-Settlement Delta Recheck

Forest's successful acknowledged refresh exposed a post-commit availability
defect: preview compared current selected component revisions only with the
immutable Builder-creation `parent_chain`. The durable capability amendment
already recorded the acknowledged discontinuity, but the same creation-to-
current parent-chain delta therefore remained available after apply.

The exact two-file delta over `924813874` now derives the current selected
chain from the newest validated `capability_refresh` or `combined` amendment's
`resulting.selected_parent_chain`. It walks amendment history newest-first,
skips additive history, and retains the immutable creation chain as the
no-refresh fallback. Artifact loading validates the complete durable amendment
shape, identity, chain rows, sequence, and capability delta before this helper
is reached. The original manifest `parent_chain`, selections, creation
provenance, and prior amendment entries remain unchanged.

The enhanced atomic-refresh regression proves the successful amendment and
config digest settle the next preview to unavailable without removing the
durable audit record. The independent reviewer reran the exact NoDb update,
auth, browser-token, project-update route, and update-worker boundary: 177
tests passed. `git diff --check` passed for the two-file delta. No delta
correctness findings remain: High 0; Medium 0; Low 0.

The previously noted combined-update test-granularity gap is closed without a
production change. `test_schema_v3_combined_update_applies_one_amendment` now
reopens preview after apply and asserts that availability is false and no
capability refresh remains. The test passed independently (1 passed), directly
covering settlement through the `combined` amendment branch.

## Validation Evidence

The package records a clean full run of 7,218 Python tests with 63 skipped and
107 frontend suites with 808 tests, plus lint, stubtests, test-stub checks,
broad-exception enforcement, vulture, documentation, diff, and synchronized RQ
graph gates.

The independent reviewer additionally ran:

- 500 focused Python tests spanning stored/live authority, hot-path dispatch,
  run-page/Flask presentation, paired climate/landuse/soil mutation, RQ
  discovery/orchestration, update routes, and the update worker: all passed;
- 259 focused Python tests spanning update persistence/recovery, locale
  authority, reader compatibility, exact OpenAPI, and run-page authorization:
  all passed;
- 19 `project_config_update` Jest tests: all passed;
- frontend ESLint: passed;
- `wctl check-rq-graph`: passed; and
- `git diff --check` against the reader-floor base: passed.

## Residual Acceptance Boundary

Forest remains the required live-system gate. It must exercise the canonical
five-locale matrix, all three Continental US station databases, one real
acknowledged eligible schema-v3 refresh, reopen, and rollback to the recorded
reader floor with byte-for-byte config/manifest preservation. The generated
`controllers-gl.js` bundle is rebuilt by the image/startup workflow and must be
confirmed current during that deployment. Those are deployment acceptance
steps, not unresolved implementation findings.

The dedicated implementation security review is recorded separately in
`20260827_security_review.md`. Its preexisting out-of-scope archive-descendant
hardening observation remains outside the ratified WP12D changed-consumer set
and does not change this correctness disposition.
