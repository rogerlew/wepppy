# WP02 — Scope Reset Cookie-Clear Targets

> **Purpose**: Limit `POST /api/auth/reset-browser-state` cookie deletion to cookies WEPPcloud actually owns, instead of emitting generic `csrf_token`/`csrftoken` deletions across parent-domain variants.
> **Target**: Codex
> **Created**: 2026-07-27
> **Status**: Active
> **Security gate**: Part of a `high`-triage package; covered by the package security review.

## Context

`_clear_reset_browser_state_cookies` (`wepppy/weppcloud/routes/weppcloud_site.py:829`) builds deletion targets via `_cookie_clear_targets` (`:804`) and `_domain_variants` (`:783`). For each cookie name it emits `delete_cookie` across every path variant × every domain variant, and the domain variants include parent-domain forms (`base` and `.base`) derived from the configured cookie domain, `request.host`, `OAUTH_REDIRECT_HOST`, and `EXTERNAL_HOST`. The cookie names include generic `csrf_token` and `csrftoken` (`:844-853`).

Independent-review finding 4: where WEPPcloud shares a parent domain with a sibling application, resetting can erase that sibling's same-named parent-domain CSRF cookie. This is caller-local (only the caller's browser) and pre-existing, but broader than "WEPPcloud cookies only."

- Current state: generic CSRF cookie names cleared across parent-domain variants.
- Goal state: clear only names and path/domain tuples WEPPcloud owns, per a documented cookie contract.

## Objective

Reset clears exactly the cookies WEPPcloud sets (session, remember, and WEPPcloud's own CSRF cookie under its own path/domain), and no generic parent-domain cookie that could belong to a sibling app — while still fully clearing WEPPcloud state so the reset remains effective.

## Working Set

### Files to Read (Inputs)
- `wepppy/weppcloud/routes/weppcloud_site.py:783-872` — the cookie-clear helpers and specs.
- `wepppy/weppcloud/configuration.py` — the actual configured cookie names, paths, and domains (`SESSION_COOKIE_*`, `REMEMBER_COOKIE_*`, CSRF cookie config).
- `docs/schemas/weppcloud-csrf-contract.md`, `weppcloud-session-contract.md` — where the owned-cookie set should be documented.

### Files to Modify (Outputs)
- `wepppy/weppcloud/routes/weppcloud_site.py` — restrict `_clear_reset_browser_state_cookies` targets to owned names/domains; drop generic parent-domain `csrf_token`/`csrftoken` deletion unless the contract documents WEPPcloud as owning them at that scope.
- Contract doc — enumerate the owned cookie set the reset is allowed to clear.
- `tests/weppcloud/routes/test_rq_engine_token_api.py` (owns the reset endpoint tests) — assert the precise expected target set; assert no generic parent-domain deletion is emitted.

### Files to Avoid (Exclusions)
- The same-origin guard (WP01) and report redaction (WP03).
- Do not change what the reset clears server-side (Flask session) or the client storage clearing.

## Instructions
1. Enumerate WEPPcloud's actually-configured cookies from `configuration.py`. Decide, per the contract, which the reset owns and at what path/domain.
2. Narrow `_clear_reset_browser_state_cookies` to those. If WEPPcloud's CSRF cookie is genuinely owned, keep it at WEPPcloud's own path/domain only — not parent-domain variants shared with siblings.
3. Keep the reset effective: after the change, a WEPPcloud session/remember/CSRF cookie is still fully removed for the caller's browser.
4. Document the owned-cookie set in the contract.
5. Test the exact target enumeration.

## Validation Gates
- `wctl run-pytest tests/weppcloud/routes/test_rq_engine_token_api.py`
- `wctl run-npm lint` / `wctl run-npm test`
- Manual: reset in a dev session still clears WEPPcloud session/remember/CSRF cookies.

## Deliverables
1. Scoped cookie-clear targets; no generic parent-domain deletion.
2. Documented owned-cookie set.
3. Exact-target-enumeration tests.

## Handoff Format
Report per the tracker's Progress Notes convention, listing the before/after target set.

---

## Outcome (Complete this when retiring the prompt)

**Completed**: YYYY-MM-DD
**Agent**:
**Result**:
**Deviations**:
**References**:
