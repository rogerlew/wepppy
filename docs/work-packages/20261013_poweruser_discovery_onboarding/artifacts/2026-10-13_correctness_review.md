# Correctness and User-Experience Review - PowerUser discovery and onboarding (PUUX-01)

Status: correctness/UX review passes for the Forest-validated candidate; validation limitations retained below.

## Metadata

- Reviewer: independent Codex reviewer `/root/contract_correctness`.
- Timestamp: 2026-10-13 19:06 UTC.
- Contract checkpoint: `2f9f94443`; candidate: `3df2ec482` (runtime `ed80608fe`, implementation parent `175f235a0`). Later candidate commits change tests only.
- Scope: Runs discovery, Profile completion/internal disclosure, shared feature-access JavaScript, run/report panel, getting-started guide and catalog registration. Reviewer did not edit runtime files.
- Authority: [PUUX-01](../../../ui-docs/contracts/poweruser-onboarding-contract.md), [feature-access governance](../../../schemas/feature-access-governance-contract.md) PUUX amendment, and [controller contract](../../../ui-docs/controller-contract.md).
- Evidence: [validation receipt](2026-10-13_validation.md), [browser receipt](forest-onboarding-browser.json), [database readback](forest-grant-readback.json), [final presentation](forest-presentation-readback.json), [source identity](source-identity.json). Dedicated [security review](2026-10-13_security_review.md) remains a separate gate.

## User Outcome

Ordinary users discover advanced tools from Runs, understand the responsibilities,
enable access immediately, and reach a fresh Profile with useful next steps.
Existing PowerUser, Admin and Root users avoid redundant onboarding. PowerUser
does not imply internal membership or acknowledgment.

Only a valid granted response completes the client flow. The form is replaced
before refreshing; the fixed same-origin recovery link also reloads when the
current fragment already matches. Failure preserves error feedback and retry.
A grant may persist despite a lost response, so Profile reload is the recovery
path; the existing idempotent endpoint prevents duplicate acceptance.

## Valid-State Matrix

| State | Required behavior | Direct evidence |
| --- | --- | --- |
| Ordinary viewer, no runs | Discovery and onboarding available | Forest browser, account 2249 |
| Ordinary viewer, populated runs | Same notice; table/map and controls retained | Forest browser, account 2250 |
| Admin viewing another user's catalog | Viewer roles govern discovery | Presentation regression |
| Newly granted PowerUser | One acceptance, refreshed heading and destinations | Browser plus independent database readback |
| Legacy PowerUser without acceptance | Active access; no fabricated acceptance/action | Browser/database account 2251; render test |
| Admin/Root without literal PowerUser | Existing-role explanation; no acquisition form | Browser/database accounts 2252/2253 |
| Dev without PowerUser | Onboarding available | Browser/database account 2254 |
| No internal memberships | Closed voluntary details; no automatic acknowledgment | Browser/database and render tests |
| Current/pending or inactive/expired membership | Open details, unchanged status/action | Render regressions; no live membership mutation |
| Access-store unavailable | Explicit unavailable message; no false empty/active state | Render regression |
| Malformed success or failed request | No false activation; actionable retry/refresh | JS tests; live CSRF/stale/anonymous rejection |

Role, membership, catalog-owner and request-response dimensions have separate
evidence; this is not an exhaustive Cartesian matrix claim.

## User-Reachable Error Policy

| Condition | Classification and visible behavior | Evidence |
| --- | --- | --- |
| Missing CSRF or stale statement | Expected rejection; preserve server error and Profile retry guidance | Live HTTP 400/409 and JS tests |
| Expired/anonymous session | Expected rejection; no success, sign-in guidance | Live anonymous rejection; client tests |
| Network failure, non-JSON or malformed success | Exceptional outcome; no active-state claim, retry enabled | Focused JS cases |
| Optional membership absent | Valid closed-details state, never an exception | Render/browser evidence |
| Membership service unavailable | Explicit reference-bearing unavailable state | Render regression |
| Guide missing from navigation | Catalog contract failure, corrected | Initial 3 failures; final 64 usersum checks pass |

## Generated Artifact Evidence Chain

| Stage | Semantics and evidence | Result |
| --- | --- | --- |
| User intent | Browser checks both affirmative inputs and submits unchanged versioned payload | Pass |
| Reloaded persisted state | Real database reader finds exactly one acceptance, PowerUser/User roles, no internal membership or acknowledgment | Pass |
| Generated intermediate | Existing usersum manifest/navigation/index pipeline; 64 contract/index/route checks and actual linked guide HTTP 200 | Pass |
| Prepared/executable input | No model preparation, serializer, scientific parameter or queue change | N/A |
| Execution output | No scientific execution/output writer changes | N/A |
| User-facing result | Actual Profile GET after grant, focus, active status, Builder access, notice removal, served guide, panel Details and compact notice | Pass |

The browser uses real sessions, CSRF, persistence and endpoints. Fixture session
creation bypasses password/CAP login; interactive login is not claimed.
Real missing-CSRF, stale-statement and internal-batch denial exercise the existing
boundaries without replacing them with request mocks.

Forest accounts are disposable new identities. The populated account temporarily
joins the existing disposable `sabbatical-stitcher` project; existing account
roles and project content are unchanged. No production deployment is claimed.
Final candidate evidence includes the compact template correction and generated
usersum catalog refresh. Independent hash readback matches all 20 recorded source
files; the served feature-access JavaScript matches its source hash. The final
presentation receipt confirms a 136px desktop notice, 390px viewport readback,
guide HTTP 200, reachable voluntary acknowledgment, panel task headings and
Technical details that start closed and expand normally.

The canonical contract's new Delivery and recovery section correctly records
paired manifest/navigation registration, generated-index rebuild, served-link
verification, direct static JavaScript, no migration/backfill, and preservation
of legitimate grants during rollback. This retains the observed catalog
requirement outside the package. The cleanup receipt records all 18 disposable
accounts deactivated, sessions and test-run associations removed, authentication
uniquifiers rotated and all three acceptance records retained; existing accounts
are unchanged.

## Review Checks and QA

- Canonical intent, valid legacy roles, optional absence and recoverable failures
  were reviewed independently of implementation assertions.
- No server route, transaction, statement version, permission registry, queue or
  scientific behavior changed. Shared internal acknowledgment and membership
  administration completion remain compatible.
- The report trigger uses the same PowerUser/Admin/Root guard as its modal.
  Comparison preserves 22 panel resource calls, 2 project-action IDs and 14
  run-token attributes. Raw state/log resources move inside native Details.
- Independent reviewer runs: 21 presentation and 16 feature-access JS tests pass.
  Final author receipts: 228 render/presentation tests, 64 usersum checks, and
  all 118 Jest suites / 980 tests pass.
- An earlier focused run stopped after 198 passes on an old report fixture
  expecting a restricted trigger while anonymous. Its explicit PowerUser context
  correction preserves the intended assertions; the 228-test rerun passes.
- Broad Python coverage completed in segments: **10,723 distinct passes and 126
  skips**, with overlap/exclusion accounting in [broad coverage](broad-coverage.json).
  The original full command stopped after 10,011 passes on a bare Runs render
  fixture missing `current_user`. That fixture and a later actual catalog browser
  fixture now supply authenticated viewer context and a Profile endpoint; their
  original assertions remain intact. The first fixture's three cases pass, and
  the final 183-test segment includes the corrected SQL/HTTP/Chromium chain.
- Continuations also encountered an unchanged OpenET JWT test returning 401
  instead of 403, and a catalog TTL p95 delta of 57.4ms exceeding its 50ms limit.
  Their complete modules pass in isolation (52 and 24 tests respectively).
  Collection-time canonical auth-module replacement is a plausible order-sensitivity
  cause, not a proved diagnosis. Timing failure cause remains unproven. No auth
  implementation, latency threshold or corresponding assertions were changed.
  This evidence does **not** constitute a clean single full-suite pass.
- Compact-notice presentation/Run-scope validation passes 36 tests. Retained
  [automated receipts](automated-checks.txt) disclose earlier failures and reruns.
- Frontend lint retains the preexisting unrelated
  `controllers_js/__tests__/climate.test.js:300` conditional-expect failure.
  That file is unchanged; lint must not be reported as passed.
- Inspected Profile, desktop/narrow Runs and panel screenshots show usable new
  controls. The panel retains a four-column grid for two leading groups, leaving
  desktop whitespace; a two-column arrangement is an optional low-priority
  polish follow-up, not a functional blocker. Existing narrow Runs search/table/
  theme overflow remains outside this change. Scripted keyboard/focus evidence
  is not general WCAG certification or an observed-user usability study.
- Tests cover persistence, legacy-state and failure contracts. Template changes
  reuse existing primitives without new frameworks or fallback layers.

## Findings

| ID | Severity | Finding and disposition | Status |
| --- | --- | --- | --- |
| PUUX-I01 | Medium | Same-fragment recovery link could not reload roles. Shared `refreshProfile()` now handles automatic/manual refresh; independent JS tests and live navigation/focus pass. | Resolved |
| PUUX-I02 | Low | Network errors omitted recovery instructions. PowerUser-only catch adds reload/retry/sign-in guidance; other forms preserved and JS tests pass. | Resolved |
| PUUX-I03 | Medium | Guide manifest lacked required navigation entry, failing 3 catalog/index tests. Candidate registers it in existing Advanced and Operations; 64 usersum checks pass and linked guide returns HTTP 200. | Resolved |
| PUUX-I04 | Low | Runs notice inherited the global panel's 256px minimum height. Correction reuses neutral `wc-alert` styling without alert semantics and preserves an inline CTA; 36 scoped tests pass and final desktop notice is 136px. | Resolved |

## Verdict

- Correctness/UX gate: **pass**; unresolved findings: high 0, medium 0, low 0.
- Forest feature acceptance is complete for the recorded candidate. The broad
  suite, lint and general layout limitations above remain explicit; they are not
  rewritten as clean passes or proved unrelated root causes.
- Release recommendation: **ship** the reviewed scope through canonical operator
  rollout after the separate security gate. No production deployment or production
  verification is claimed. Integration QA was performed by the implementation
  agent; this review is independent correctness/UX/QA assessment, not a third
  independent QA execution.
- Reviewer: `/root/contract_correctness`, 2026-10-13 UTC.

## Artifact Observability Gate

No run-scoped scientific files or archive members are created. The comparable
workflow is existing Profile feature access: role and versioned acceptance stay
in the established account database and are visible through Profile under normal
account authorization. Private account records/session credentials are not
project archive contents.

The guide uses the existing usersum catalog pipeline; real authenticated linked
page readback closes its rendered-content boundary. Database readback and Profile
consumption directly verify onboarding. Model-input,
failure-artifact retention and project archive/restore tests are N/A because no
such writer, path or policy changed. No observability exception is introduced.
