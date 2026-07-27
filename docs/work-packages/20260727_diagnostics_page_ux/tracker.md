# Tracker – Diagnostics Page UX, Browser Reset Relocation, and Discoverability

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-27 20:20 UTC
**Current phase**: Scoped / ready for implementation
**Last updated**: 2026-07-27 20:20 UTC
**Next milestone**: WP01 (run feedback + re-run) implemented and passing gates
**Security impact**: `high` (scoped to WP02 reset endpoint auth posture)
**Dedicated security review**: `yes` (WP02 only)
**Security artifact**: `docs/work-packages/20260727_diagnostics_page_ux/artifacts/<date>_security_review.md`

## Task Board

### Ready / Backlog
- [ ] WP01 — Live run feedback + re-run control (Codex; `prompts/active/wp01_run_feedback_rerun.prompt.md`)
- [ ] WP02 — Browser Session Reset relocation + anonymous auth posture (Codex; `prompts/active/wp02_browser_reset_relocation.prompt.md`; security review artifact required)
- [ ] WP03 — Card density + More-menu/usersum discoverability wiring (Codex; `prompts/active/wp03_layout_density_discoverability.prompt.md`)
- [ ] WP04 — Author usersum end-user doc, register in manifest/nav, regenerate index (Claude Code; after WP01–WP03 land, or stub first per `enduser-stub-authoring-guide.md`)

### In Progress
- (none)

### Blocked
- (none)

### Done
- [x] Package scoped and scaffolded (2026-07-27 20:20 UTC)

## Sequencing

WP01 → WP02 → WP03 → WP04, serially. WP01–WP03 all touch `diagnostics.htm`; serial execution avoids template merge conflicts. WP04 documents the shipped UX.

## Decisions Log

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
| Anonymous reset endpoint becomes an annoyance vector (forced logout via CSRF) | Medium | Low | Retain same-origin POST check + CSRF token; security review verifies | Open |
| WP01–WP03 template conflicts | Low | Medium | Serial execution per Sequencing | Open |
| More-menu change on interfaces.htm regresses anonymous Cap/login flow | Low | Low | Keep Login link; menu addition is additive; manual smoke on anonymous view | Open |
| Spec drift (`diagnostics-page.spec.md` not updated with behavior changes) | Medium | Medium | Each WP prompt includes a spec-amendment deliverable; verify at closure | Open |

## Verification Checklist

### Code Quality
- [ ] `wctl run-pytest tests/weppcloud/routes/test_diagnostics_page.py` passing
- [ ] `wctl run-npm lint` clean
- [ ] `wctl run-npm test` passing (diagnostics Jest suites updated)
- [ ] Playwright smoke specs under `static-src/tests/smoke/diagnostics/` updated or confirmed unaffected

### Security
- [ ] WP02 security review artifact present and complete
- [ ] No unresolved medium/high findings
- [ ] Anonymous reset path: same-origin + CSRF verified, no session/user info in response, caller-only effect

### Documentation
- [ ] `docs/ui-docs/diagnostics-page.spec.md` amended for all shipped behavior
- [ ] usersum doc published, registered in `docs_manifest.yaml` / `nav_tree.yaml`, `docs_index.json` regenerated via `tools/usersum_docs_tool.py`
- [ ] Diagnostics page links to the usersum doc
- [ ] Package closure notes complete

### Deployment
- [ ] Verified in docker-compose.dev stack (anonymous + authenticated sessions)
- [ ] forest1 test-production smoke if applicable

## Progress Notes

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
