# Diagnostics Page UX, Browser Reset Relocation, and Discoverability

**Status**: Open (2026-07-27)
**Timezone**: UTC

## Overview

The `/weppcloud/diagnostics/` page (route `GET /diagnostics/` on `weppcloud_site_bp`, anonymous-accessible) validates browser/runtime prerequisites but has poor run feedback: checks take 30+ seconds while the page shows a static "Running diagnostics..." placeholder, there is no way to re-run checks without reloading, the card layout is visually loose with excessive vertical spacing, and the page is not discoverable — no nav entry exists for it and no end-user documentation covers it. Separately, the Browser Session Reset control lives on `/weppcloud/profile/`, which requires login; users with corrupted browser state may be unable to log in at all, so the reset belongs on the anonymous-accessible diagnostics page.

## Objectives

- Live per-check feedback while diagnostics run: users can see which checks are pending, running, and finished, plus overall progress, at any point during the 30+ second run.
- A re-run control that repeats all checks in place without a page reload.
- Browser Session Reset relocated from the profile page to the diagnostics page and usable by anonymous users (security-gated decision, see below).
- Tighter, denser card layout consistent with `docs/ui-docs/ui-style-guide.md`.
- Discoverable from the interfaces page "More" dropdown for both anonymous and authenticated users, and from usersum via a new end-user doc.

## Scope

### Included
- `wepppy/weppcloud/templates/diagnostics/diagnostics.htm` and `wepppy/weppcloud/static/js/diagnostics/` (page.js, core.js, report.js orchestration; check modules only as needed for progress events).
- Relocation of the Browser Session Reset section and its inline script out of `wepppy/weppcloud/templates/user/profile.html` into the diagnostics page, with the script extracted to a static module.
- Auth posture decision and any change to `POST /api/auth/reset-browser-state` (`wepppy/weppcloud/routes/weppcloud_site.py`), which currently returns 401 for anonymous callers.
- "More" dropdown in `wepppy/weppcloud/templates/interfaces.htm`: render for anonymous users and add a Diagnostics entry for all users.
- New usersum end-user doc for the diagnostics page, registered in `docs_manifest.yaml` / `nav_tree.yaml` with regenerated `docs_index.json`.
- Amendments to the authoritative spec `docs/ui-docs/diagnostics-page.spec.md` for every behavior change.
- Test updates: `tests/weppcloud/routes/test_diagnostics_page.py`, `tests/weppcloud/routes/test_rq_engine_token_api.py` (owns the reset endpoint tests), `tests/weppcloud/routes/test_user_profile_token.py` (asserts the profile reset context variables), and Jest suites under `wepppy/weppcloud/controllers_js/__tests__/` (diagnostics_*). Note: `static-src/tests/smoke/diagnostics/` is unrelated deck.gl/map-rendering diagnostics, not this page's suite.

### Explicitly Out of Scope
- Adding new diagnostic checks or changing check semantics/thresholds.
- Shortening check durations by changing probe sizes or timeout budgets (bandwidth/realtime probes keep their current budgets; this package makes the wait legible, not shorter).
- `bootstrap_observability.js` and run-page status streaming.
- Profile page redesign beyond removing the reset section and linking to diagnostics.
- Nav changes on templates other than `interfaces.htm`.

## Stakeholders

- **Primary**: WEPPcloud end users and support workflows ("open diagnostics, copy the report, send it to us").
- **Reviewers**: Roger Lew.
- **Security Reviewer**: Required for WP02 (reset endpoint auth posture).
- **Implementation**: Codex (WP01–WP03). **Documentation**: Claude Code (WP04 usersum doc).

## Success Criteria

- [ ] Within one second of page load, the check list shows every registered check with a pending/running state; states update live as each check starts and settles; an overall progress indicator (completed-of-total) is visible during the run.
- [ ] A re-run control repeats all checks without a page reload, guards against overlapping runs, and re-gates Copy JSON until the new run settles.
- [ ] Browser Session Reset is available on `/weppcloud/diagnostics/` for anonymous and authenticated users; the profile page section is removed and replaced with a link to diagnostics; the inline script is extracted to a shared static module.
- [ ] The interfaces page "More" dropdown renders for anonymous users and includes a Diagnostics entry for all users.
- [ ] A usersum end-user doc explains what the page is for, how to read blocker/degraded/info results, how to copy and share the report, and when to use Browser Session Reset; it is indexed and linked from the diagnostics page.
- [ ] Card layout is denser per the UI style guide; spec updated to match.
- [ ] `docs/ui-docs/diagnostics-page.spec.md` reflects all shipped behavior.
- [ ] `wctl run-pytest tests/weppcloud/routes/test_diagnostics_page.py`, `wctl run-npm lint`, and `wctl run-npm test` pass.

## Dependencies

### Prerequisites
- None. Builds on the shipped diagnostics page (spec and wave boards in `docs/ui-docs/diagnostics-page.*`).

### Blocks
- WP03's usersum link requires a registered doc target: a stub at `wepppy/weppcloud/routes/usersum/weppcloud/diagnostics.md` (per `enduser-stub-authoring-guide.md`) MUST land before WP03 so the page never links to a missing doc. The full WP04 doc lands after WP01–WP03 so it describes the shipped UX.

## Related Packages
- **Related**: [20260727_auth_session_persistence_hardening](../20260727_auth_session_persistence_hardening/package.md) — same auth/session surface; the reset endpoint decision must not contradict the persistence contract ratified there.

## Timeline Estimate
- **Expected duration**: 2–4 focused sessions
- **Complexity**: Medium
- **Risk level**: Low overall; Medium for WP02 (auth surface)

## Security Impact and Review Gate

- **Security impact triage**: `high`
- **Dedicated security review required**: `yes` (scoped to WP02)
- **Triage rationale**: WP01/WP03/WP04 are presentation, nav, and docs changes with no attack-surface delta. WP02 changes an auth/session surface: `POST /api/auth/reset-browser-state` currently rejects anonymous callers (401) and enforces same-origin POST; relocating the control to an anonymous-accessible page implies relaxing that 401 so logged-out users with corrupted state can self-serve. Repo policy treats auth/session changes as high by default. The review should confirm: same-origin and CSRF enforcement retained, no session data or user info leaked in the anonymous response path, no cross-user effect (the endpoint only clears the caller's own cookies/session), and abuse potential (rate limiting) considered.
- **Security review artifact**: `docs/work-packages/20260727_diagnostics_page_ux/artifacts/<date>_security_review.md` (required before WP02 closes)

## Parameterization ADR Gate

- **Parameterization change present**: `no`
- **ADR required**: `no`

## References
- `docs/ui-docs/diagnostics-page.spec.md` — authoritative page spec; must be amended with every behavior change
- `docs/ui-docs/ui-style-guide.md` — layout/density conventions
- `wepppy/weppcloud/routes/weppcloud_site.py` — `diagnostics()` route (~line 1062), `reset_browser_state()` (~line 874), `_clear_reset_browser_state_cookies()` (~line 829)
- `wepppy/weppcloud/templates/user/profile.html` — Browser Session Reset section + inline script (from ~line 107)
- `wepppy/weppcloud/routes/user.py` — profile view passes `reset_browser_state_endpoint` / `reset_browser_state_login_url` (~lines 482–496)
- `wepppy/weppcloud/templates/interfaces.htm` — `header_nav` block with auth-only "More" menu (~lines 24–77)
- `wepppy/weppcloud/static/js/diagnostics/` — page.js (DOMContentLoaded runner), core.js (check registry/runner), bandwidth_checks.js (4 s RTT / 12 s download / 12 s upload probe budgets), diagnostics-realtime.js (20 s probe windows with reconnect retry), report.js
- `wepppy/weppcloud/routes/usersum/weppcloud/enduser-authoring-guide.md` and `enduser-stub-authoring-guide.md` — doc authoring conventions
- `tools/usersum_docs_tool.py` — manifest/nav validation and `docs_index.json` regeneration

## Deliverables
[Fill at closure]

## Follow-up Work
[Fill at closure]
