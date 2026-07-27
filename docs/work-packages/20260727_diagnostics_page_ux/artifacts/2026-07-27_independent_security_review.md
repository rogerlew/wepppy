# Independent Security Review — Diagnostics UX Implementation

**Reviewed**: implementation diff `280e7f9d5^..HEAD` (WP01 `1503e1ece`, WP02 `324169a37`, WP03 `cdf73f2aa`)
**Reviewer**: Codex, fresh thread 019fa584-a359-7173-8868-d3b5ca570fb4, read-only, told not to trust the implementer's self-review
**Verified & dispositioned by**: Claude Code, 2026-07-27 21:44 UTC (each finding checked against source before disposition)
**Reviewer verdict**: anonymous reset surface safe to ship for forced-logout/cross-user; low-severity hardening noted. Implementer artifact judged "not adequate as a complete independent review" — sound ship verdict but missed residual risks.

## Why this pass exists

The WP02 security artifact was authored by the implementing agent (Codex wrote the change and its own review). This is an independent pass in a fresh context to close that gap, per the user's request.

## Verification method

For each finding I read the cited source rather than accepting the reviewer's claim. Key checks: `_is_same_origin_post` / `_allowed_origin_set` (weppcloud_site.py:357/327), `_clear_reset_browser_state_cookies` / `_cookie_clear_targets` (783–872), `reset_browser_state` response (874–905), `browser_reset.js` storage clearing, `register_csrf_exemptions` (1196), and the WP diff scope of `report.js` / `auth_checks.js`.

## Findings and Dispositions

| # | Sev | Finding | Verified? | Disposition |
|---|-----|---------|-----------|-------------|
| 1 | Info | Cross-site forced logout blocked: reset route not CSRF-exempt, CSRFProtect runs before handler, same-origin gate after. | **Confirmed** — `register_csrf_exemptions` (line 1198) exempts only `issue_rq_engine_operator_token`; reset is not listed. | No action. Confirmation retained. |
| 2 | Low | `_is_same_origin_post` returns true for `Sec-Fetch-Site: same-origin` without checking a conflicting `Origin`; `_allowed_origin_set` trusts `X-Forwarded-*`. | **Confirmed at lines 357-360, 338-343.** | **Pre-existing shared helper**, unchanged by this WP; also guards `issue_rq_engine_token` (line 388). Not browser-exploitable (CSRF independently required). Out of scope for a diagnostics WP → **follow-up on the shared same-origin helper** (see below). |
| 3 | Info | Anonymous response discloses no session/user state. | **Confirmed** — response body is exactly `ok`/`login_url`/`message`; `cleared_session_keys` removed in WP02. | No action. |
| 4 | Low | Cookie clear emits generic `csrf_token`/`csrftoken` deletions across parent-domain variants; could clear a sibling app's same-named cookie sharing the parent domain. | **Confirmed at lines 844-853 + `_domain_variants` 783-801.** | **Pre-existing** `_clear_reset_browser_state_cookies`, unchanged by WP02 (diff was only the 401/count removal). Only material if WEPPcloud shares a parent domain with a sibling app using identical cookie names. → **follow-up**. |
| 5 | Info | No new unauthenticated DoS/amplification. | **Confirmed** — bounded session clear + fixed header set, no I/O/queue/loops. | No action. |
| 6 | Low | `browser_reset.js` clears any key prefixed `wc-` or `wepp` (4 chars); reviewer suggested tightening `wepp` → `wepp-`. | **Verified — and the recommended fix is UNSAFE here.** Production stores `weppcloud:fork-console:...` (no hyphen); `wepp-` would orphan it and break the reset. Prefix logic is carried over verbatim from the original profile inline script. | **Fix rejected.** Broad prefix is required on this single-purpose origin. Behavior kept as-is; rationale recorded. |
| 7 | Info | Reset redirect not attacker-controlled (`url_for('security.login')` only). | **Confirmed** — no user input reaches `login_url`. | No action. Optional client-side same-origin guard noted as defense-in-depth, not taken (server cannot emit an external URL). |
| 8 | Info | Card rendering has no XSS sink (all `textContent`/text nodes). | **Confirmed** — page.js uses textContent; template attrs Jinja-autoescaped. | No action. Reviewer's `CSS.escape` suggestion for future extension IDs noted; current IDs are trusted constants. |
| 9 | Info | Nav change exposes only the Diagnostics link to anonymous users; admin/role entries stay gated. | **Confirmed** in interfaces.htm diff. | No action. |
| 10 | Low | "Redacted" Copy JSON uses a denylist; `auth_checks.js` copies arbitrary backend error text into evidence; realtime evidence includes full WS hostname. | **Confirmed pre-existing** — `report.js` untouched by this WP; `auth_checks.js` diff only added `description` fields; Copy JSON predates the WP. | Real latent concern about the "redacted" claim → **follow-up on report redaction (allowlist)**. Not a regression introduced here. |
| 11 | Info | Implementer's WP02 artifact missed findings 2/4/6/10 and overstated "Accepted residual risks: None." | **Agreed.** | **Amend** `2026-07-27_wp02_security_review.md` residual-risk section (done alongside this artifact). |

## Outcome

- **Ship verdict stands.** No high/medium browser-exploitable finding. The package closure is not reopened for a blocker.
- **No code change from this pass.** Finding 6's recommended fix was rejected on verified evidence; findings 2/4/10 are pre-existing and out of a diagnostics WP's scope.
- **Doc corrections:** WP02 self-review residual-risk section corrected; follow-ups recorded below.

## Follow-ups (not blocking; logged for a future security-hardening package)

1. **Shared same-origin helper** (`_is_same_origin_post`/`_allowed_origin_set`): make `Sec-Fetch-Site: same-origin` non-authoritative when a conflicting `Origin` is present; source allowed origins from proxy-normalized data or a fixed configured public origin rather than client `X-Forwarded-*`. Affects every caller of the helper, not just reset — must be scoped and tested on its own.
2. **Cookie clear targets**: restrict `_clear_reset_browser_state_cookies` to cookie names/domains WEPPcloud owns; drop generic `csrf_token`/`csrftoken` parent-domain deletions unless part of a documented cookie contract.
3. **Report redaction**: rebuild the Copy JSON report from an allowlist of fixed diagnostic codes/messages instead of embedding arbitrary backend exception text and absolute WS hostnames.
4. **Test hardening**: add CSRF-enabled integration tests exercising the anonymous origin/header matrix (valid token, absent token, missing Origin+Referer, `Origin: null`, scheme/port/subdomain mismatch, `Sec-Fetch-Site: cross-site`); the current route unit fixture does not initialize `CSRFProtect`.
