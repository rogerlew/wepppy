# Tracker – Diagnostics Page UX, Browser Reset Relocation, and Discoverability

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-27 20:20 UTC
**Current phase**: Closed — all workstreams shipped
**Last updated**: 2026-07-27 21:25 UTC
**Next milestone**: forest1 test-production smoke on next deploy (operational follow-up, outside package scope)
**Security impact**: `high` (scoped to WP02 reset endpoint auth posture)
**Dedicated security review**: `yes` (WP02 only)
**Security artifact**: `docs/work-packages/20260727_diagnostics_page_ux/artifacts/2026-07-27_wp02_security_review.md`

## Task Board

### Ready / Backlog
- (none)

### In Progress
- (none)

### Blocked
- (none)

### Done
- [x] Package scoped and scaffolded (2026-07-27 20:20 UTC)
- [x] WP04a — usersum stub `weppcloud/diagnostics.md` authored, registered in manifest/nav, index rebuilt, doc-lint clean (2026-07-27 21:00 UTC; executed in parallel with WP01 — working sets disjoint, land-before-WP03 constraint preserved)
- [x] WP01 — live check cards per spec 4.1/4.2, progress indicator, guarded Re-run; Codex-implemented, gates independently re-verified (pytest 6, Jest 656), prompt retired with outcome (2026-07-27 21:08 UTC)
- [x] WP02 — Browser Session Reset relocated to diagnostics for anonymous/authenticated callers; CSRF + same-origin posture verified; security gate passed with zero unresolved findings (2026-07-27 21:09 UTC)
- [x] WP03 — compact diagnostics composition plus More-menu/usersum discoverability; anonymous live response and both auth-state template renders verified; review fix: neutralized `.wc-panel` min-height/margins on check rows (2026-07-27 21:18 UTC)
- [x] WP04b — full Browser Diagnostics usersum guide replacing the stub (live cards, re-run, report sharing, Browser Session Reset); index rebuilt 72/72, doc-lint clean (2026-07-27 21:22 UTC)

## Sequencing

WP01 → WP02 → WP04a (usersum stub) → WP03 → WP04b (full doc), serially. WP01–WP03 all touch `diagnostics.htm`; serial execution avoids template merge conflicts. The stub precedes WP03 so the page's usersum link never targets a missing doc; the full doc lands last so it describes the shipped UX. Canonical usersum doc path: `wepppy/weppcloud/routes/usersum/weppcloud/diagnostics.md` (category `weppcloud`, filename `diagnostics.md`).

## Decisions Log

### 2026-07-27: WP02 anonymous CSRF and contract classification
**Context**: WP02 requires anonymous callers on diagnostics to receive a usable CSRF token before `POST /api/auth/reset-browser-state` stops returning 401.

**Decision**: No normative amendment to `weppcloud-csrf-contract.md` or `weppcloud-session-contract.md` is required. Diagnostics extends `base_pure.htm`, whose CSRF meta tag invokes `csrf_token()` for anonymous and authenticated sessions; `browser_reset.js` submits that token as `X-CSRFToken`. Global `CSRFProtect` validates it before route dispatch, and the endpoint retains its explicit normalized same-origin gate. This conforms to the CSRF contract's existing cookie-authenticated mutator classification (validated token, with an additional same-origin gate). The session contract delegates route-level CSRF classification to that contract and does not define reset response fields or require authentication for caller-local session clearing.

**Impact**: Anonymous and authenticated callers use the same protected path. The response is reduced to `ok`, `login_url`, and a generic message; reset has no identifier input and affects only the requesting browser's cookies and Flask session.

### 2026-07-27 20:55 UTC: Codex scaffold review — all 8 findings accepted and applied
**Context**: Codex reviewed commit 783095311 (scaffold + spec 4.1) at Roger's request. Full findings and dispositions: `artifacts/2026-07-27_codex_scaffold_review.md`.

**Decision**: All 8 findings accepted; fixes applied to the spec, all three WP prompts, package.md, and this tracker. Load-bearing corrections: check definitions gain a `description` field (WP01 now owns the check modules for that); spec `info` impact language no longer contradicts the fix-hint rule; WP02 must disposition `weppcloud-csrf-contract.md` / `weppcloud-session-contract.md` and confirm anonymous pages get a usable CSRF token before relaxing the 401; reset endpoint tests live in `test_rq_engine_token_api.py` and profile context tests in `test_user_profile_token.py`; a registered usersum stub (WP04a) precedes WP03; bandwidth budgets corrected to 4/12/12 s; `static-src/tests/smoke/diagnostics/` recorded as unrelated deck.gl diagnostics.

**Impact**: Sequencing is now WP01 → WP02 → WP04a → WP03 → WP04b; scaffold verdict upgraded from "not fully executable as written" to executable.

### 2026-07-27 20:20 UTC: Reset control moves to diagnostics; endpoint posture decided in WP02
**Context**: Browser Session Reset lives on the login-gated profile page, but its primary audience is users whose browser state is broken badly enough that login may fail. `POST /api/auth/reset-browser-state` currently 401s anonymous callers.

**Options considered**:
1. Keep endpoint auth-required; show reset on diagnostics only when authenticated — defeats the support scenario for logged-out users.
2. Allow anonymous same-origin POST; endpoint clears only the caller's own cookies/session — serves the scenario; enlarges anonymous surface; requires security review.

**Decision**: Recommend option 2, gated on the WP02 security review confirming same-origin + CSRF enforcement, no info leak in the anonymous response, and no cross-user effect. Final call rests with the security review.

**Impact**: Package triaged `high`; WP02 cannot close without the security artifact.

### 2026-07-27 20:40 UTC: Check card contract ratified into spec section 4.1
**Context**: Roger reviewed a rendered check card showing "pass Severity: Blocker" plus a fix hint on a passing check. Root cause: `renderChecks` in `page.js` appends the raw severity taxonomy and fix hint to every card unconditionally, and the spec had no card presentation contract for Codex to build against.

**Decision**: Claude Code added section 4.1 (Check Card Presentation Contract) to `docs/ui-docs/diagnostics-page.spec.md`: one live card per check updating in place through queued/running/settled states; raw severity words (`blocker`/`degraded`/`info`) never rendered in card text — on warn/fail they translate to plain-language impact statements; fix hints and evidence render only on warn/fail; JSON report model unchanged. WP01's prompt now implements to that contract.

**Impact**: WP01 scope grows to include card content rules and plain-language check copy, not just chip states. Acceptance criteria in the spec extended to match.

### 2026-07-27 20:20 UTC: Make the wait legible, not shorter
**Context**: The 30+ second run time comes from bandwidth probe and realtime probe timeout budgets that exist to produce meaningful measurements.

**Decision**: WP01 improves feedback (live per-check states, progress, re-run) without changing probe sizes or timeout budgets. Shortening budgets would change check semantics and is out of scope.

**Impact**: Keeps WP01 purely presentational; no re-validation of check thresholds needed.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Anonymous reset endpoint becomes an annoyance vector (forced logout via CSRF) | Medium | Low | Retain same-origin POST check + CSRF token; security review verifies | Mitigated |
| Anonymous sessions may lack a usable CSRF token, making the relocated reset uncallable | Medium | Medium | WP02 step 2 verifies against the CSRF contract before shipping; contract amended if needed | Resolved |
| WP01–WP03 template conflicts | Low | Medium | Serial execution per Sequencing | Resolved |
| More-menu change on interfaces.htm regresses anonymous Cap/login flow | Low | Low | Keep Login link; menu addition is additive; manual smoke on anonymous view | Resolved |
| Spec drift (`diagnostics-page.spec.md` not updated with behavior changes) | Medium | Medium | Each WP prompt includes a spec-amendment deliverable; verify at closure | Resolved |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/weppcloud/routes/test_diagnostics_page.py` passing
- [x] `wctl run-npm lint` clean
- [x] `wctl run-npm test` passing (diagnostics Jest suites updated)
- [x] Playwright smoke specs under `static-src/tests/smoke/diagnostics/` confirmed unrelated deck.gl diagnostics

### Security
- [x] WP02 security review artifact present and complete
- [x] No unresolved medium/high findings
- [x] Anonymous reset path: same-origin + CSRF verified, no session/user info in response, caller-only effect

### Documentation
- [x] `docs/ui-docs/diagnostics-page.spec.md` amended for WP01/WP02/WP03 behavior
- [x] usersum doc published (stub then full guide), registered in `docs_manifest.yaml` / `nav_tree.yaml`, `docs_index.json` regenerated via `tools/usersum_docs_tool.py`
- [x] Diagnostics page links to the usersum doc
- [x] Package closure notes complete

### Deployment
- [x] Verified in docker-compose.dev stack (anonymous + authenticated sessions)
- [ ] forest1 test-production smoke if applicable — operational follow-up on next deploy

## Progress Notes

### 2026-07-27 21:25 UTC: WP04b complete; package closed
**Agent/Contributor**: Claude Code

**Work completed**:
- Reviewed WP03 diff; caught and returned one review finding on-thread (`.wc-panel` min-height:256px + 2xl margins still applied to check rows — invisible to curl/jsdom validation); Codex fixed with page-scoped `min-height: 0; margin: 0` plus regression assertions; gates re-verified independently (pytest 72, Jest 657); committed as cdf73f2aa.
- Expanded `usersum/weppcloud/diagnostics.md` from stub to full Browser Diagnostics guide covering live check rows, progress counter, re-run, impact/what-to-do/technical-detail reading, redacted report sharing, Browser Session Reset (including the signed-out rationale), and limits. Validator 72/72, doc-lint clean.
- Closed package.md with deliverables and closure notes; PROJECT_TRACKER entry moved to Done.

**Next steps**: none in-package. forest1 smoke on next deploy is the remaining operational step.

### 2026-07-27 21:18 UTC: WP03 density and discoverability complete
**Agent/Contributor**: Codex

**Work completed**:
- Consolidated the intro, readiness summary, live check roster, and report controls into one compact diagnostics surface while keeping Browser Session Reset separate.
- Scoped all density CSS beneath `#diagnostics_page_root`; used style-guide spacing tokens, existing status chips, panels, buttons, and toolbar utilities without changing shared primitives.
- Added the registered `weppcloud/diagnostics.md` usersum link.
- Made More → Diagnostics available for anonymous and authenticated interface navigation while retaining anonymous Login and authenticated role-aware entries.
- Added both-auth-state template coverage and amended the normative layout/discoverability contract.

**Validation**:
- Pytest: diagnostics 6 passed; interface template selection 7 passed; interface route 2 passed.
- Frontend: ESLint passed; Jest 87 suites / 657 tests passed.
- Docs: diagnostics spec doc-lint passed with 0 errors and 0 warnings; uk2us preview had no changes.
- Dev stack: anonymous `/interfaces/` and `/diagnostics/` returned 200; rendered Login, More → Diagnostics, compact diagnostics root, reset card, and resolved usersum link. Authenticated navigation was verified by Jinja render coverage rather than a live signed-in browser session.

**Next steps**: Review the uncommitted WP03 working tree; execute WP04b after acceptance.

### 2026-07-27 21:09 UTC: WP02 Browser Session Reset relocation complete
**Agent/Contributor**: Codex

**Work completed**:
- Moved Browser Session Reset and its client behavior from profile to diagnostics; the profile now links to diagnostics.
- Allowed anonymous endpoint calls while retaining global CSRF validation and explicit same-origin validation; removed session-key counts from the fixed generic response.
- Verified that anonymous diagnostics sessions receive a usable CSRF token from `base_pure.htm`; recorded why the existing CSRF/session contracts require no normative amendment.
- Added route/template/storage regression coverage and amended diagnostics spec section 4.3.
- Completed `artifacts/2026-07-27_wp02_security_review.md`: 3 findings (2 Medium, 1 Low), all resolved; zero unresolved High/Medium/Low findings.

**Validation**:
- Pytest: diagnostics 6 passed; reset/token API 38 passed; profile 15 passed.
- Frontend: ESLint passed; Jest 87 suites / 657 tests passed.
- Dev stack: anonymous CSRF success, missing-CSRF rejection, cross-origin rejection, browser storage clearing/redirect, and authenticated reset all verified.

**Next steps**: Review the uncommitted WP02 working tree; execute WP03 after acceptance.

### 2026-07-27 20:55 UTC: Codex review dispositioned
**Agent/Contributor**: Codex (review) + Claude Code (disposition)

**Work completed**:
- Codex's read-only review of commit 783095311 returned 8 findings (5 medium, 3 low); all accepted and applied. See `artifacts/2026-07-27_codex_scaffold_review.md`.
- Files corrected: `docs/ui-docs/diagnostics-page.spec.md` (description field, info-language fix), all three WP prompts, `package.md`, this tracker.

**Next steps**: unchanged — Codex executes WP01; note the revised sequencing places the WP04a usersum stub before WP03.

### 2026-07-27 20:20 UTC: Package scaffolded
**Agent/Contributor**: Claude Code

**Work completed**:
- Scoped the four workstreams from Roger's feedback (run feedback/re-run, reset relocation, layout density, discoverability + end-user doc).
- Verified current state: static "Running diagnostics..." placeholder in `diagnostics.htm`; no re-run affordance in `page.js`; reset section + ~150-line inline script in `profile.html` posting to an auth-required endpoint; interfaces.htm More menu rendered only for authenticated users; no usersum doc for the page.
- Authored package.md, tracker.md, and WP01–WP03 Codex prompts.

**Next steps**:
- Codex executes WP01 per `prompts/active/wp01_run_feedback_rerun.prompt.md`.
- Claude Code authors the usersum doc (WP04) after WP01–WP03 land.

## Communication Log

### 2026-07-27: Package initiated
**Participants**: Roger Lew, Claude Code
**Topic**: Roger identified five gaps on `/weppcloud/diagnostics/`: unclear run feedback over a 30+ second run, no re-run button, Browser Session Reset stranded on the login-gated profile page, ugly/loose card formatting, and no discoverability (nav or usersum) for logged-in or anonymous users.
**Outcome**: This package.
