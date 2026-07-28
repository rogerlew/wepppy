# WP01 — Same-Origin Guard Parity

> **Purpose**: Make one normative same-origin contract that all three WEPPcloud request guards implement identically, so a genuinely same-origin POST is authorized regardless of proxy TLS-termination topology.
> **Target**: Codex
> **Created**: 2026-07-27
> **Status**: Active
> **Security gate**: This package is triaged `high`. A dedicated security review artifact is required before closure; do not weaken any guard.
> **Hard dependency**: WP00 must be complete and its reviewed standalone
> checkpoint revision must be recorded in the tracker before this prompt edits
> implementation or test files.

## Context

Three same-origin guards exist and diverge:
- Flask `wepppy/weppcloud/routes/weppcloud_site.py`: `_is_same_origin_post` (`:357`), `_allowed_origin_set` (`:327`). Accepts `Sec-Fetch-Site: same-origin` first; then Origin against the allowed set; then Referer. Builds allowed origins from `request.host_url`, `request.scheme`/`request.host`, and client `X-Forwarded-Proto`/`X-Forwarded-Host`.
- rq-engine `wepppy/microservices/rq_engine/session_routes.py`: `_is_same_origin_cookie_request` (`:291`), `_allowed_origin_set` (`:259`). Same shape, also reads `X-Forwarded-Ssl`.
- query-engine `wepppy/query_engine/app/server.py`: `_is_same_origin_request` (`:206`), `_request_allowed_origins` (`:177`). **No `Sec-Fetch-Site` fast-path** — Origin-only. This is why `POST /query-engine/diagnostics/bandwidth/upload` returns `403 cross_origin_blocked` for a same-origin request on deployments where TLS terminates upstream of Caddy (Caddy forwards `X-Forwarded-Proto: http`, so the reconstructed allowed origin is `(http, host, 80)` and never matches the browser's `(https, host, 443)`). It works on `wepp.cloud` only because Caddy terminates TLS there and `{scheme}` = `https`.

Two problems to fix together:
1. **Missing fast-path** (correctness/robustness): query-engine should accept `Sec-Fetch-Site: same-origin` like the other two, so a same-origin POST does not depend on the proxy reconstructing the scheme.
2. **Over-trust** (hardening; independent-review finding 2): none of the guards should treat `Sec-Fetch-Site: same-origin` as authoritative when a conflicting `Origin` header is present, and forwarded-origin candidates should derive from proxy-normalized data or a configured public origin rather than blindly trusting client `X-Forwarded-*`.

- Current state: three ad-hoc guards; query-engine 403s same-origin POSTs behind upstream TLS.
- Goal state: one documented contract, three conforming implementations, robust to topology, no weaker than today against cross-origin.
- Related: `docs/work-packages/20260727_web_origin_guard_hardening/package.md`; independent-review artifact in the diagnostics package.

## Objective

Author a normative same-origin contract and conform all three guards to it. A same-origin browser POST (which carries `Sec-Fetch-Site: same-origin`) is authorized on every proxy topology; a cross-origin request, an `Origin` conflicting with the page origin, or a spoofed forwarded header is rejected exactly as today or more strictly.

**Success looks like**: the bearhive upload probe passes; no test asserting cross-origin rejection regresses; all three guards pass the same shared test vectors.

Before any implementation work, verify that the tracker names a full WP00
checkpoint revision and that revision is an ancestor of `HEAD`. Stop if either
condition fails.

## Working Set

### Files to Read (Inputs)
- The three guard implementations named above (both the predicate and its allowed-origin builder in each).
- `docs/schemas/weppcloud-csrf-contract.md`, `docs/schemas/weppcloud-session-contract.md` — where the contract is documented.
- `wepppy/weppcloud/app.py` ProxyFix configuration — how many proxy hops are trusted for the Flask app.
- `docker/caddy/Caddyfile`, `Caddyfile.wepp1` — what the proxy actually forwards (`X-Forwarded-Proto {scheme}`, `Host {host}`, no `X-Forwarded-Host` for query-engine).

### Files to Modify (Outputs)
- `wepppy/query_engine/app/server.py` — add the `Sec-Fetch-Site: same-origin` fast-path to `_is_same_origin_request`; align `_request_allowed_origins` with the contract.
- `wepppy/weppcloud/routes/weppcloud_site.py` and `wepppy/microservices/rq_engine/session_routes.py` — apply the Origin-conflict and forwarded-trust hardening from the contract.
- `docs/schemas/weppcloud-csrf-contract.md` — add the normative same-origin section (fast-path precedence, Origin-conflict rule, forwarded-origin derivation, decision order) and the shared test-vector table. (Claude Code may author this doc section; coordinate.)
- Unit tests colocated with each guard for the contract's decision table (the cross-surface integration matrix is WP04).

### Files to Reference (Dependencies)
- `wepppy/weppcloud/static/js/diagnostics/bandwidth_checks.js` — the upload probe whose POST is the live symptom; do not change here.

### Files to Avoid (Exclusions)
- `docker/caddy/Caddyfile*` — the proxy scheme fix is an operational companion, not this WP.
- The diagnostics upload-probe UX (relabeling a 403) — related follow-up on the diagnostics package.
- Any endpoint that does not currently enforce same-origin — do not broaden coverage.

## Contract

The reviewed normative contract is
`docs/schemas/weppcloud-csrf-contract.md` section "Browser Same-Origin Guard
Contract." Do not use this prompt's historical context as authority.

Implement its exact decision order, including missing-signal rejection, raw
forwarded-header non-authority, and the sole HTTP:80 application to HTTPS:443
same-host bridge under `Sec-Fetch-Site: same-origin`. The legacy rq-engine
forwarded-origin environment variable remains accepted but inert.

## Validation Gates
- `wctl run-pytest` for the weppcloud, query-engine, and rq-engine suites touching these guards.
- `wctl run-npm lint` / `wctl run-npm test`.
- Simulated upstream-TLS check: construct an authoritative application request
  tuple of HTTP:80 with `Origin: https://host:443` and
  `Sec-Fetch-Site: same-origin`; expect authorization. Raw
  `X-Forwarded-Proto`/`X-Forwarded-Host` alone must not create an allowed
  origin. Cross-site or conflicting host/explicit port must reject.

## Deliverables
1. Three conforming guards; query-engine same-origin POST authorized behind upstream TLS.
2. Normative same-origin contract section + shared test vectors in the CSRF contract doc.
3. Unit coverage of the decision table per guard.

## Handoff Format
Report per the tracker's Progress Notes convention: changes per file, the final decision table, test output, and any point where a guard could not conform identically (and why).

---

## Outcome (Complete this when retiring the prompt)

**Completed**: YYYY-MM-DD
**Agent**:
**Result**:
**Deviations**:
**References**:
