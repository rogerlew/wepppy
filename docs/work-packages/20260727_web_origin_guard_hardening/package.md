# Web Same-Origin Guard Parity and Data-Boundary Hardening

**Status**: Open - contract checkpoint required before implementation
**Timezone**: UTC

## Overview

Independent security review of the diagnostics work package, plus a same-day root-cause investigation of an "Upload speed → warn" report, surfaced a set of low-severity but real defects in WEPPcloud's browser-facing request guards. The unifying problem: same-origin enforcement is implemented three times, inconsistently, across three services, and two related data-boundary behaviors (reset cookie clearing, diagnostics report redaction) are broader/weaker than advertised. None is individually shippable-blocking; together they are a coherent hardening package with one already-observable production symptom.

The observable symptom: on deployments where TLS is terminated **upstream** of Caddy (e.g., `wc.bearhive.duckdns.org`), the query-engine bandwidth upload probe returns `403 cross_origin_blocked` for a genuinely same-origin POST. It works on `wepp.cloud` only because that node's Caddy terminates TLS itself, so `{scheme}` resolves to `https`. The application should not depend on proxy topology to authorize a same-origin request.

## Objectives

- One normative same-origin contract, implemented identically by all three guards, robust to proxy TLS-termination topology.
- Reset cookie clearing scoped to cookies WEPPcloud actually owns.
- Diagnostics Copy JSON report built from an allowlist, not a denylist.
- A shared same-origin/CSRF test matrix that actually exercises the failure modes.

## Execution Authority and Sequencing

This package is UI-coupled and governed by
`docs/standards/contract-first-change-standard.md`. Execute the active umbrella
ExecPlan at
`prompts/active/web_origin_guard_hardening_execplan.md`.

WP00 is a hard prerequisite. It must register this package as a bounded
remediation, finalize and amend the canonical contracts, obtain two independent
checkpoint reviews, disposition their findings, and create a standalone
documentation-only ancestor commit. WP01-WP04 must not edit implementation
files until that full revision is recorded in the tracker and is an ancestor of
the implementation.

The bounded-remediation registration is REM-04 under GOV-00A-M1D. It borrows
only SURF-13, SHR-02, and SHR-04A and does not change the Pure UI register's
Diagnostics exclusion.

## Scope

### Included
- **Same-origin guard parity** across the three implementations:
  - Flask `wepppy/weppcloud/routes/weppcloud_site.py` `_is_same_origin_post` (`:357`) / `_allowed_origin_set` (`:327`) — has a `Sec-Fetch-Site` fast-path; trusts client `X-Forwarded-*`.
  - rq-engine `wepppy/microservices/rq_engine/session_routes.py` `_is_same_origin_cookie_request` (`:291`) / `_allowed_origin_set` (`:259`) — has a `Sec-Fetch-Site` fast-path; trusts `X-Forwarded-*`/`X-Forwarded-Ssl`.
  - query-engine `wepppy/query_engine/app/server.py` `_is_same_origin_request` (`:206`) / `_request_allowed_origins` (`:177`) — **no `Sec-Fetch-Site` fast-path** (Origin-only); the outlier that 403s same-origin POSTs behind upstream TLS.
- **Cookie-clear scoping**: `_clear_reset_browser_state_cookies` (`weppcloud_site.py:829`) emits generic `csrf_token`/`csrftoken` deletions across parent-domain variants (`_domain_variants` `:783`).
- **Report redaction**: `wepppy/weppcloud/static/js/diagnostics/report.js` `redactText` (`:123`) is a four-pattern denylist; `auth_checks.js` copies arbitrary backend error text into evidence; realtime evidence embeds the full WebSocket hostname.
- **Test matrix**: one shared origin-predicate matrix plus per-surface
  CSRF/authentication/boundary integration tests.
- Contract documentation: extend `docs/schemas/weppcloud-csrf-contract.md` (or a new same-origin sub-contract) with the normative rules and shared test vectors.

### Explicitly Out of Scope
- Per-node Caddy `X-Forwarded-Proto` correction on upstream-TLS-terminated deployments (e.g., bearhive). This is the *infra* root cause of the observed 403 and is tracked as an **operational companion** below; WP01 makes the application correct regardless, but the proxy misconfiguration should also be fixed on affected nodes. Deployment-affecting; needs node owner go-ahead and the terminator's trusted-proxy CIDR.
- Diagnostics upload-probe UX relabeling ("blocked/failed" vs "slow"). Real defect (a 403 rendered as an "Upload speed" warning), but it belongs to the diagnostics UX surface — tracked as a **related follow-up** to `20260727_diagnostics_page_ux`. WP01 removes the 403 symptom on affected nodes; the relabel hardens the display independently.
- Broadening the same-origin guard to endpoints that do not currently enforce it.

## Stakeholders
- **Primary**: WEPPcloud operators of non-canonical (upstream-TLS) deployments; the browser-request security surface generally.
- **Reviewers**: Roger Lew.
- **Security Reviewer**: Required (this package changes CSRF/same-origin enforcement).
- **Implementation**: Codex (code + tests). **Contract docs**: Claude Code.

## Success Criteria
- [ ] A single documented same-origin contract; all three guards conform, verified by shared test vectors.
- [ ] A genuinely same-origin POST is authorized regardless of whether TLS terminates at or upstream of the proxy (query-engine gains the `Sec-Fetch-Site` fast-path; the bearhive upload probe passes).
- [ ] `Sec-Fetch-Site: same-origin` is not treated as authoritative when a conflicting `Origin` is present; forwarded-origin candidates derive from proxy-normalized data or a configured public origin, not blindly-trusted client `X-Forwarded-*`.
- [ ] Reset cookie clearing targets only WEPPcloud-owned names/domains; no generic parent-domain `csrf_token`/`csrftoken` deletion unless documented as owned.
- [ ] Copy JSON report is assembled from fixed diagnostic codes/messages; no arbitrary backend exception text or absolute WS hostname leaks; denylist retained only as defense-in-depth.
- [ ] Shared predicate tests cover missing signals, `Origin: null`,
  scheme/port/subdomain mismatch, and cross-site on all three guards; separate
  tests cover valid/missing/invalid Flask-WTF tokens, rq-engine cookie/session
  authentication, and query-engine boundary controls.
- [ ] `wctl run-pytest` (affected suites), `wctl run-npm lint`, `wctl run-npm test` pass.

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: the package changes CSRF/same-origin enforcement across three request guards and two data-boundary behaviors — auth-adjacent by the repo's default-high criteria. The review must confirm the parity change does not *weaken* any guard (e.g., a too-permissive `Sec-Fetch-Site` acceptance, or forwarded-header trust that enables origin spoofing where a proxy passes attacker-controlled headers).
- **Security review artifact**: `docs/work-packages/20260727_web_origin_guard_hardening/artifacts/<date>_security_review.md` (required before closure).

## Parameterization ADR Gate
- **Parameterization change present**: `no`
- **ADR required**: `no`

## Hardening and Callus Softening
- **Failure signature(s)**: `POST /query-engine/diagnostics/bandwidth/upload` → `403 cross_origin_blocked` on upstream-TLS deployments; same-origin browser POSTs authorized only where the proxy reconstructs `https`. Evidence line: `http_status=403. error_code=cross_origin_blocked.`
- **Related prior hardening**: `20260727_diagnostics_page_ux` (independent security review that logged findings 2/4/10), `20260727_auth_session_persistence_hardening` (adjacent auth surface).
- **Health signals**: same-origin POSTs authorized across proxy topologies; no new cross-origin acceptance; test matrix green.
- **Danger signals**: any guard accepting a request whose `Origin` conflicts with the page origin; forwarded-header trust admitting an attacker-supplied origin.
- **Observation window**: 14-30 days post-deploy on an upstream-TLS node.

## Related Packages
- **Depends on**: none.
- **Related**: [20260727_diagnostics_page_ux](../20260727_diagnostics_page_ux/package.md) (source of findings 2/4/10 and the upload-probe UX follow-up), [20260727_auth_session_persistence_hardening](../20260727_auth_session_persistence_hardening/package.md).

## Operational Companion (tracked, not a code WP)
- Caddy `X-Forwarded-Proto {scheme}` on upstream-TLS nodes forwards the connection scheme (`http`) rather than the client scheme (`https`). Fix per node: a global `servers { trusted_proxies static <terminator-CIDR> }` so `{scheme}` adopts the upstream `X-Forwarded-Proto`, or per-block pass-through of the incoming header. Hand-edited config (`docker/caddy/Caddyfile*`); node-owner go-ahead required. `wepp.cloud`/`wepp1` is unaffected (Caddy terminates TLS there).

## References
- `docs/work-packages/20260727_diagnostics_page_ux/artifacts/2026-07-27_independent_security_review.md` — findings 2/4/10 and the follow-up list this package executes.
- `wepppy/query_engine/app/server.py:206,258,309` — query-engine same-origin guard + bandwidth handlers.
- `wepppy/weppcloud/routes/weppcloud_site.py:327,357,829` — Flask guard + cookie clear.
- `wepppy/microservices/rq_engine/session_routes.py:259,291` — rq-engine guard.
- `wepppy/weppcloud/static/js/diagnostics/report.js:123` — report redaction denylist.
- `docs/schemas/weppcloud-csrf-contract.md`, `docs/schemas/weppcloud-session-contract.md` — contracts to extend.
- `docker/caddy/Caddyfile`, `docker/caddy/Caddyfile.wepp1` — proxy scheme handling.

## Deliverables

- Active umbrella ExecPlan and living tracker.
- Contract decision, bounded-remediation registration, canonical amendments,
  dual checkpoint reviews, disposition, and standalone checkpoint ancestor.
- WP01-WP04 implementation and regression evidence.
- Dedicated final security review and independent correctness review.
- Closure notes and archived completed prompts.

## Follow-up Work
[Fill at closure]
