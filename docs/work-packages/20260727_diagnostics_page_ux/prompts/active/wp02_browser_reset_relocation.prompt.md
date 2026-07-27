# WP02 — Relocate Browser Session Reset to the Diagnostics Page

> **Purpose**: Move the Browser Session Reset control from the login-gated profile page to the anonymous-accessible diagnostics page so users with broken browser state can self-serve before login.
> **Target**: Codex
> **Created**: 2026-07-27
> **Status**: Active
> **Security gate**: This WP is the reason the package is triaged `high`. It cannot close without a security review artifact at `docs/work-packages/20260727_diagnostics_page_ux/artifacts/<date>_security_review.md` using `docs/prompt_templates/security_review_template.md`.

## Context

The Browser Session Reset section lives in `wepppy/weppcloud/templates/user/profile.html` (section marked `data-browser-reset-root`, followed by an inline script of roughly 150 lines) and posts to `POST /api/auth/reset-browser-state` in `wepppy/weppcloud/routes/weppcloud_site.py`. The endpoint currently returns 401 for anonymous callers and enforces same-origin POST. The client side clears localStorage/sessionStorage keys prefixed `wc-` or `wepp`, then follows the returned login URL. The profile view in `wepppy/weppcloud/routes/user.py` passes the endpoint and login URL into the template.

The placement is backwards: the users who most need the reset are those whose cookies or storage are corrupted badly enough that login itself misbehaves. They cannot reach the profile page. The diagnostics page is anonymous-accessible and is where support will send these users.

- Current state: reset control on profile only; endpoint auth-required.
- Goal state: reset control on `/weppcloud/diagnostics/` for anonymous and authenticated users; profile section removed and replaced with a link to the diagnostics page; inline script extracted to a static module; endpoint posture decided and reviewed.
- Related work: `docs/work-packages/20260727_auth_session_persistence_hardening/` ratified the current authentication persistence contract — the reset behavior must not contradict it. Package decision log recommends allowing anonymous same-origin POSTs (tracker.md, Decisions Log).

## Objective

An anonymous user on the diagnostics page can trigger Browser Session Reset: the server clears its cookies for the site and their (possibly empty) session, the client clears `wc-`/`wepp`-prefixed storage, and the user is directed to the login URL. An authenticated user gets the same behavior the profile page provides today. The profile page section is gone, replaced by a pointer to diagnostics.

**Success looks like**: a support instruction of "open /weppcloud/diagnostics/ and click Reset browser state" works whether or not the user can log in.

## Working Set

### Files to Read (Inputs)
- `wepppy/weppcloud/templates/user/profile.html` — current section markup and the full inline script (message handling, busy state, storage clearing, CSRF header, redirect flow)
- `wepppy/weppcloud/routes/weppcloud_site.py` — `reset_browser_state()`, `_clear_reset_browser_state_cookies()`, `_is_same_origin_post()`
- `wepppy/weppcloud/routes/user.py` — profile view wiring of `reset_browser_state_endpoint` and `reset_browser_state_login_url`
- `docs/ui-docs/diagnostics-page.spec.md` — where the reset section fits the page contract
- `docs/work-packages/20260727_diagnostics_page_ux/tracker.md` — Decisions Log entry on the auth posture

### Files to Modify (Outputs)
- `wepppy/weppcloud/routes/weppcloud_site.py` — relax the anonymous 401 per the decision below; keep same-origin enforcement; ensure the anonymous response reveals nothing about any session or user
- `wepppy/weppcloud/static/js/diagnostics/` — new module holding the extracted reset client logic (storage clearing, CSRF header, messaging, busy state, redirect); loaded from the diagnostics template
- `wepppy/weppcloud/templates/diagnostics/diagnostics.htm` — reset section (own card or section per the spec), including the cautionary copy explaining what the reset does and that it signs the user out
- `wepppy/weppcloud/templates/user/profile.html` — remove the section and inline script; add a short pointer to the diagnostics page
- `wepppy/weppcloud/routes/user.py` — drop now-unused context variables if nothing else consumes them
- `docs/ui-docs/diagnostics-page.spec.md` — add the reset section to the page contract
- `tests/weppcloud/routes/test_diagnostics_page.py` and the reset endpoint's route tests — cover the anonymous path, same-origin rejection, and profile removal
- `docs/work-packages/20260727_diagnostics_page_ux/artifacts/<date>_security_review.md` — dedicated review artifact

### Files to Avoid (Exclusions)
- Session/remember-cookie configuration in `wepppy/weppcloud/configuration.py` — owned by the auth persistence hardening package
- Flask-Security login/logout flows — the reset must compose with them, not alter them

## Instructions

1. Read the endpoint and inline script end to end; inventory exactly what is cleared server-side (cookies via the clear-targets helper, Flask session) and client-side (prefixed storage keys).
2. Endpoint posture: allow anonymous callers. Retain the same-origin POST check and CSRF token handling. For anonymous callers the response must carry only the ok flag, login URL, and a generic message — no session key counts or any user-identifying detail. Confirm the operation only ever affects the caller's own cookies and session; there is no identifier parameter to abuse.
3. Extract the profile inline script into a static module under the diagnostics JS directory, preserving behavior: busy state, status messaging, storage clearing on success, redirect to the returned login URL. The module reads its endpoint and login URL from data attributes as the profile markup does today.
4. Add the reset section to the diagnostics template with copy that states plainly: it clears WEPPcloud cookies and site storage for this browser and signs you out. If a diagnostics run is in progress, the control should still work — the reset is independent of check execution.
5. Remove the profile section and script; leave a one-line pointer to the diagnostics page in its place. Clean up the profile view's context variables if now unused.
6. Amend the spec with the reset section contract.
7. Write the security review artifact using the template's by-surface checks, covering: anonymous access rationale, same-origin/CSRF enforcement, response information content, cross-user effect analysis, and abuse/rate-limit consideration. Close or disposition all medium/high findings.
8. Update route tests: anonymous POST succeeds and clears cookies; cross-origin POST is rejected; anonymous response carries no session detail; profile page no longer renders the section.

## Validation Gates

- `wctl run-pytest tests/weppcloud/routes/test_diagnostics_page.py`
- `wctl run-pytest tests/weppcloud/` for the reset endpoint's suite
- `wctl run-npm lint` and `wctl run-npm test`
- Manual in the dev stack: reset as an anonymous user (cookies present from a prior session) and as an authenticated user; confirm storage clearing and redirect in both cases.

## Deliverables

1. Reset control live on the diagnostics page for all users; profile section removed with pointer.
2. Extracted static module replacing the inline script.
3. Security review artifact with no unresolved medium/high findings.
4. Amended spec and passing route tests.

## Handoff Format

Report per the package tracker's Progress Notes convention. Explicitly state the final endpoint posture and link the security artifact.

---

## Outcome (Complete this when retiring the prompt)

**Completed**: YYYY-MM-DD
**Agent**:
**Result**:
**Deviations**:
**References**:
