# WP02 — Scope Reset Cookie-Clear Targets

> **Purpose**: Limit `POST /api/auth/reset-browser-state` cookie deletion to cookies WEPPcloud actually owns, instead of emitting generic `csrf_token`/`csrftoken` deletions across parent-domain variants.
> **Target**: Codex
> **Created**: 2026-07-27
> **Status**: Complete
> **Security gate**: Part of a `high`-triage package; covered by the package security review.
> **Hard dependency**: WP00 and WP01 must be complete, and the WP00 checkpoint
> revision must be an ancestor of `HEAD`.

## Context

`_clear_reset_browser_state_cookies` (`wepppy/weppcloud/routes/weppcloud_site.py:829`) builds deletion targets via `_cookie_clear_targets` (`:804`) and `_domain_variants` (`:783`). For each cookie name it emits `delete_cookie` across every path variant × every domain variant, and the domain variants include parent-domain forms (`base` and `.base`) derived from the configured cookie domain, `request.host`, `OAUTH_REDIRECT_HOST`, and `EXTERNAL_HOST`. The cookie names include generic `csrf_token` and `csrftoken` (`:844-853`).

Independent-review finding 4: where WEPPcloud shares a parent domain with a sibling application, resetting can erase that sibling's same-named parent-domain CSRF cookie. This is caller-local (only the caller's browser) and pre-existing, but broader than "WEPPcloud cookies only."

- Current state: generic CSRF cookie names cleared across parent-domain variants.
- Goal state: clear only names and path/domain tuples WEPPcloud owns, per a documented cookie contract.

## Objective

Reset clears exactly the session and remember cookies WEPPcloud sets, and no
generic parent-domain cookie that could belong to a sibling app. Flask-WTF CSRF
state is stored inside the session and is removed with the session cookie.

## Working Set

### Files to Read (Inputs)
- `wepppy/weppcloud/routes/weppcloud_site.py:783-872` — the cookie-clear helpers and specs.
- `wepppy/weppcloud/configuration.py` — the configured session and remember
  cookie names, paths, and domains.
- `docs/schemas/weppcloud-csrf-contract.md`, `weppcloud-session-contract.md` — where the owned-cookie set should be documented.

### Files to Modify (Outputs)
- `wepppy/weppcloud/routes/weppcloud_site.py` — restrict `_clear_reset_browser_state_cookies` targets to owned names/domains; drop generic parent-domain `csrf_token`/`csrftoken` deletion unless the contract documents WEPPcloud as owning them at that scope.
- Contract doc — enumerate the owned cookie set the reset is allowed to clear.
- `tests/weppcloud/routes/test_rq_engine_token_api.py` (owns the reset endpoint tests) — assert the precise expected target set; assert no generic parent-domain deletion is emitted.

### Files to Avoid (Exclusions)
- The same-origin guard (WP01) and report redaction (WP03).
- Do not change what the reset clears server-side (Flask session) or the client storage clearing.

## Instructions
0. Verify the tracker records the WP00 checkpoint revision and WP01 completion.
   Stop if the checkpoint is not an ancestor of `HEAD`.
1. Enumerate WEPPcloud's actually-configured cookies from `configuration.py`. Decide, per the contract, which the reset owns and at what path/domain.
2. Narrow `_clear_reset_browser_state_cookies` to the resolved session and
   remember tuples only. Do not retain either generic CSRF cookie name.
3. Keep the reset effective: the session deletion removes Flask-WTF state and
   the remember deletion removes remembered identity.
4. Document the owned-cookie set in the contract.
5. Test the exact target enumeration.

## Validation Gates
- `wctl run-pytest tests/weppcloud/routes/test_rq_engine_token_api.py`
- `wctl run-npm lint` / `wctl run-npm test`
- Manual: reset in a dev session clears WEPPcloud session and remember cookies;
  subsequent Flask-WTF state is fresh because the session was removed.

## Deliverables
1. Scoped cookie-clear targets; no generic parent-domain deletion.
2. Documented owned-cookie set.
3. Exact-target-enumeration tests.

## Handoff Format
Report per the tracker's Progress Notes convention, listing the before/after target set.

---

## Outcome (Complete this when retiring the prompt)

**Completed**: 2026-07-28
**Agent**: Codex
**Result**: Reset now deletes exactly the configured session and remember
cookie name/path/domain tuples, preserving configured paths and excluding
generic CSRF cookies and derived sibling-domain variants.
**Deviations**: None.
**References**: `tests/weppcloud/routes/test_csrf_rollout.py`;
`docs/schemas/weppcloud-session-contract.md`.
