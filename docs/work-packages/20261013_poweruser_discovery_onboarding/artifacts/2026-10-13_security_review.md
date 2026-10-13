# Security Review - PowerUser discovery and onboarding (PUUX-01)

## Findings and disposition

No implementation security findings were identified. Unresolved findings:
**high 0, medium 0, low 0**. No risk acceptance is requested.

**Security gate: pass for the Forest-validated candidate.** The reviewed scope
is ready for canonical operator rollout; this sign-off is not production
deployment authorization or evidence of production verification. Integration QA
is implementation-agent work; no third independent QA review is claimed.

## Scope and authority

- Reviewer: independent `contract_security` agent (security reviewer role).
- Reviewed at: 2026-10-13 19:07 UTC.
- Contract checkpoint: `2f9f944433147ee497e3c6115c25d96cc9e0b71c`.
- Final candidate: `3df2ec482edf52c3ea3d565a025ecca8432b9715`;
  runtime changes remain at `ed80608fe` (includes `175f235a0`).
- Canonical behavior: [PowerUser onboarding contract](../../../ui-docs/contracts/poweruser-onboarding-contract.md)
  and [contract decision](2026-10-13_contract_decision.md).
- Related reviews: [contract reviews](2026-10-13_contract_reviews.md),
  [correctness review](2026-10-13_correctness_review.md), and
  [validation evidence](2026-10-13_validation.md).

The operator authorized full PUUX-01 implementation and validation on Forest.
The review covers role-sensitive Runs/Profile/panel/report presentation, shared
feature-access JavaScript, registered help content, tests, and the bounded
Forest evidence drivers. It excludes production operations. The separate
PUUX-01A Dashboard navigation review is retained in its own artifact.

Security triage is **high; dedicated review required** because the changed
client completion flow handles session-authenticated privilege activation.
The backend grant API, statement version, role registry, route authorization,
and persistence implementation are unchanged.

## Surface checks

| Surface | Result and concrete evidence |
| --- | --- |
| Valid-state noninterference | Runs discovery uses `current_user`, not the selected catalog owner. Empty and populated Runs, table/map mode, ordinary and Dev-only accounts, literal PowerUser, Admin/Root without PowerUser, legacy grants without acceptance, and feature-store errors are represented in presentation tests. Admin/Root receive existing-access explanation, not a fabricated PowerUser grant or acceptance. Store `error_id` remains the first Profile branch. |
| Authentication and authorization | No diff to `routes/user.py`, `utils/feature_access_web.py`, or feature-registry authorization. Existing active-session provenance and current-account grant boundaries remain authoritative. Report panel trigger now shares the existing PowerUser/Admin/Root guard. Resource calls, project actions, read-only checks, and role guards inside the panel are preserved. Ordinary Dashboard access from PUUX-01A remains intact. |
| CSRF and request integrity | `static/js/feature_access.js` retains same-origin session credentials, CSRF header, endpoint, and payload fields. The two affirmative inputs and `poweruser-2026-10-01` statement remain unchanged. Actual Forest requests rejected missing CSRF (400), stale statement (409), and anonymous submission. The anonymous receipt proves denial, not a separately isolated session-provenance branch. |
| Activation response and navigation | Client success requires the existing nonempty message plus `result.status === "granted"`, boolean `role_changed`, and matching statement version. Failed or malformed responses remain errors. Completed controls are removed before reloading the fixed server-rendered Profile link; same-path/same-fragment navigation explicitly reloads. Destination origin is checked; no response-supplied redirect is followed. The retained refresh link uses the same handler. |
| Rendered output and error handling | Messages use `textContent`; destinations use existing template URL helpers. There is no new HTML insertion, arbitrary fetch target, deserialization, or shell input. Explicit retry/refresh/sign-in guidance remains reachable after failures. Heading focus and narrow-screen evidence support the intended completion feedback. |
| Internal access isolation | Existing membership display and voluntary acknowledgment are wrapped in Details without changing their payloads or grant rules. No-membership state remains valid; existing/expired memberships retain visibility. Forest grant readback proves zero internal memberships and no internal acknowledgment after PowerUser activation; internal batch access remains denied (403). |
| Secrets and validation identities | Browser sessions lived only in ignored `docker/secrets/puux-browser*.json` fixtures with restricted file permissions. Retained browser/DB JSON includes IDs and nonsecret assertions, not cookie values. Preparation created disposable `puux-…@example.test` accounts and only the populated account's association to the existing disposable project. Existing account permissions are unchanged. Cleanup validated exact identity/email and bounded project associations; all 18 accounts are inactive, their stored sessions and project associations removed, authentication uniquifiers rotated, and all 3 acceptance rows retained. |
| Documentation visibility | `docs_manifest.yaml` registers only the new authenticated-user guide (`min_role: user`); `nav_tree.yaml` adds its matching entry only under Advanced and Operations. Protected navigation sections are unchanged. The guide documents existing feature access and recovery without granting access. Forest served-guide readback returns 200. |
| Data integrity and concurrency | No grant transaction, acceptance schema, NoDb locking, Redis contract, or model writer changes. Actual DB readback confirms one acceptance after duplicate submission and unchanged legacy acceptance state. Legitimate role grants and acceptance history must survive deployment rollback and disposable-account cleanup. |
| Files, queues, subprocesses, and network | No production filesystem/run-tree path, output writer, queue edge, worker command, external integration, or outbound destination changes. No additional path or queue gate is applicable to this presentation-only implementation. |
| Agent tooling, CI/CD, and dependencies | No runtime tool permission, CI workflow, service identity, dependency, or deployment topology change. Review used local source and retained Forest evidence; no production access or mutation was performed. |
| Observability and recovery | Client failures remain explicit and the existing backend audit/acceptance records remain intact. Browser navigation and independent DB readback corroborate activation instead of relying on a success message alone. Validation documents source rollback and separate production rollout through canonical operator tooling. |

## Evidence reviewed

The independent reviewer inspected source, test assertions, retained logs, and
nonsecret receipts. Test execution and live browser actions were performed by
the implementation agent; no additional adversarial probes were needed.

- [Forest browser receipt](forest-onboarding-browser.json): real activation,
  actual Profile navigation and focus, notice removal, builder access,
  legacy/Admin/Root/Dev presentation, and denial cases described above.
- [Independent Forest DB receipt](forest-grant-readback.json): account 2249 has
  PowerUser/User and exactly one current-version acceptance after duplicate
  submission; no internal grant/acknowledgment. Other role fixtures retain their
  original role/acceptance states.
- [Final presentation readback](forest-presentation-readback.json): served guide
  HTTP 200, reachable voluntary internal acknowledgment, compact 136px desktop
  notice and 390px visibility, panel task headings, and functional Details.
- [Disposable-account cleanup](forest-account-cleanup.json): all 18 account IDs
  deactivated, stored sessions absent and test-run associations removed;
  acceptance count remains 3 before and after cleanup. The cleanup driver checks
  the actual database and session store before writing the receipt.
- [Source identity](source-identity.json): independently recalculated all 20
  listed file hashes with zero mismatches; the recorded served JavaScript hash
  matches the source hash. The `ed80608fe` to `3df2ec482` delta contains only two
  explicit viewer/Profile test-fixture corrections and screenshot positions.
- `tests/weppcloud/routes/test_poweruser_onboarding_presentation.py` and the
  complete controls render checks: **228 passed** (`/tmp/puux-render-final.log`).
- Focused feature-access JavaScript: **16 passed**
  (`/tmp/puux-js-final2.log`); complete frontend suite: **118 suites, 980 tests
  passed** (`/tmp/puux-npm-final.log`).
- Usersum manifest/navigation, index construction, route and shell checks:
  **64 passed** (`/tmp/puux-usersum-final.log`).
- The `ed80608fe` follow-up changes only Runs notice markup/classes and adds
  browser presentation assertions; its role condition and fixed Profile link
  are unchanged. Reviewed independently with no security findings.
- [Broad coverage accounting](broad-coverage.json) and
  [retained check output](automated-checks.txt): **10,723 distinct passed,
  126 skipped**, completed in segments, not a clean single full-suite run.
  The initial missing-viewer fixture was corrected. An unchanged OpenET JWT
  admission assertion returned 401 instead of 403 in reduced collection, then
  all 52 module tests passed in isolation. Inspection confirms existing
  collection-time canonical `sys.modules` replacement in `test_auth_tokens.py`;
  order sensitivity is plausible, not conclusively established. An unchanged
  catalog latency assertion measured 57.4ms against 50ms, then all 24 module
  tests passed on rerun. The final 183-test segment passed. None of these
  admission or latency implementations was changed by PUUX.
- `git diff --check`: passed. Existing feature-access server authorization and
  mutation implementations are absent from the implementation diff.
- Frontend lint has an unrelated existing failure at
  `controllers_js/__tests__/climate.test.js:300`
  (`jest/no-conditional-expect`); that file is unchanged. This is a disclosed
  validation limitation, not a PUUX security finding.

## Final evidence checklist

- [x] Contract and implementation reviewed independently against the bounded
  operator-authorized behavior.
- [x] Actual authenticated Forest grant and negative requests observed.
- [x] Durable acceptance and role state independently read from Forest DB.
- [x] Valid legacy/Admin/Root/Dev and empty/populated states checked.
- [x] Shared internal-access and membership client behavior covered by focused
  tests; no corresponding backend authorization changes.
- [x] Guide registration and protected navigation preservation checked.
- [x] Final served guide/panel presentation receipt inspected.
- [x] All 18 disposable identities deactivated, their test-run associations and
  stored sessions removed, authentication uniquifiers rotated, and acceptance
  history retained; cleanup receipt inspected.
- [x] Broad Python suite outcome recorded and failures triaged with limitations.
- [x] Implementation-agent integration QA and source/evidence binding inspected.
- [x] Completed independent correctness/UX disposition inspected before final
  security sign-off; no separate independent QA gate is claimed.

The independent correctness artifact passed at 19:06 UTC for the same candidate.
Its resolved same-fragment recovery, error guidance, guide registration, and
notice-layout findings are supported by the focused tests and final live
readbacks. No unresolved correctness finding prevents this security sign-off.

## Artifact observability and residual scope

This change produces no scientific/run-tree artifact, input intermediate,
archive member, or new artifact writer. Native writer, failure-retention, and
archive/restore gates are therefore not applicable; no observability exception
is requested. The changed user workflow persists existing role/acceptance
records, which are covered by live Profile rendering and independent DB
readback. Evidence artifacts remain in this package.

The durable contract's Delivery and recovery section requires the existing
usersum index rebuild, canonical web refresh, and an ordinary authenticated
guide-200 check during rollout. Paired presentation/catalog rollback preserves
legitimate role grants and acceptance history. This accurately records the
observed stale-index failure and its bounded recovery.

No new security residual risk was identified within the candidate. Browser
fixtures exercise real sessions and mutations but bypass password/CAP login;
this review makes no claim about that unchanged login experience, participant
usability outcomes, or production deployment. Segmented Python completion and
the unchanged lint failure limit a general regression-cleanliness claim; they
do not establish a PUUX security defect. The existing auth-test module isolation
issue is a scoped follow-up, not an authorization change in this package.

## Sign-off

Independent security review: `contract_security`, 2026-10-13 19:07 UTC,
**pass; high 0, medium 0, low 0 unresolved security findings**. Final disposition
follows the completed independent correctness/UX review and the implementation
agent's integration QA. No production operation was performed by this reviewer.
