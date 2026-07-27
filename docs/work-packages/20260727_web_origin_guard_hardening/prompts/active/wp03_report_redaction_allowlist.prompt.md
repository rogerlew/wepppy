# WP03 — Allowlist-Based Diagnostics Report Redaction

> **Purpose**: Rebuild the diagnostics Copy JSON report from an allowlist of fixed diagnostic codes/messages so it cannot leak arbitrary backend error text or internal hostnames.
> **Target**: Codex
> **Created**: 2026-07-27
> **Status**: Active
> **Security gate**: Part of a `high`-triage package; covered by the package security review.

## Context

`wepppy/weppcloud/static/js/diagnostics/report.js` `redactText` (`:123`) applies four regex denylist patterns (`authorization`, `token`, `cookie`, JWT-shaped) to check evidence and fix hints. Independent-review finding 10: this is a denylist, so anything not matching those patterns passes through. Two concrete leaks:
- `auth_checks.js` copies arbitrary backend error messages into `evidence` (e.g., a token-mint failure returns `JWT configuration error: {exception}`), which the "redacted" report then embeds verbatim — internal hostnames, paths, key identifiers, connection strings, emails would survive.
- Realtime evidence embeds the full current WebSocket hostname.

The Copy JSON report is meant to be safe to paste into a public bug report.

- Current state: denylist redaction over free-form backend text.
- Goal state: report assembled from fixed, known-safe diagnostic codes and messages; free-form backend text not included; denylist retained only as defense-in-depth.

## Objective

The redacted report contains only allowlisted fields and fixed message text keyed by diagnostic outcome. No arbitrary backend exception string, no absolute WebSocket URL/hostname, appears in the copied JSON. On-page cards may still show fuller detail (they are not copied/shared), but the copied artifact is allowlist-built.

## Working Set

### Files to Read (Inputs)
- `wepppy/weppcloud/static/js/diagnostics/report.js` — `redactText` (`:123`), `redactCheck` (`:134`), `redactReport` (`:159`), `toRedactedJson`.
- `wepppy/weppcloud/static/js/diagnostics/auth_checks.js` — where backend error text enters `evidence`.
- `wepppy/weppcloud/static/js/diagnostics/diagnostics-realtime.js` — where the WS hostname enters evidence.
- `wepppy/weppcloud/static/js/diagnostics/bandwidth_checks.js` — evidence composition (includes server-provided detail).
- `docs/ui-docs/diagnostics-page.spec.md` §4 (report model), §9 (security/privacy).

### Files to Modify (Outputs)
- `report.js` — build the report from an allowlist: fixed per-check fields (id, title, severity, status) plus a bounded, sanitized evidence value derived from known diagnostic codes/messages rather than raw backend text. Keep the denylist as a final defense-in-depth pass.
- Possibly `auth_checks.js` / `diagnostics-realtime.js` — attach a structured, safe result code/detail the report can map to fixed text, instead of relying on free-form strings for the copied artifact. Do not change probe semantics.
- `docs/ui-docs/diagnostics-page.spec.md` — amend §9 to state the report is allowlist-built and enumerate what the copied artifact may contain.
- `wepppy/weppcloud/controllers_js/__tests__/` — assert the redacted report excludes injected backend error text and absolute WS hostnames.

### Files to Avoid (Exclusions)
- The same-origin guard (WP01) and cookie clearing (WP02).
- On-card rendering behavior (section 4.1) — this WP governs the copied JSON, not the live card display.

## Instructions
1. Define the allowlist: which fields and which fixed messages the copied report may contain per check status/outcome.
2. Reshape report assembly so free-form backend `evidence` is not copied verbatim; map known outcomes to fixed strings; drop or route unknown text to a generic placeholder.
3. Remove absolute WS hostnames from the copied evidence (route-only or omitted).
4. Keep `redactText` as a last-pass safety net.
5. Amend the spec; add tests that inject a hostile evidence string and assert it does not appear in `toRedactedJson`.

## Validation Gates
- `wctl run-npm lint` / `wctl run-npm test`
- `wctl run-pytest tests/weppcloud/routes/test_diagnostics_page.py`
- Manual: trigger an auth-check failure with a synthetic backend message; confirm Copy JSON omits it.

## Deliverables
1. Allowlist-built redacted report; no arbitrary backend text or absolute hostname.
2. Spec §9 amended.
3. Injection-style redaction tests.

## Handoff Format
Report per the tracker's Progress Notes convention; include the allowlist definition.

---

## Outcome (Complete this when retiring the prompt)

**Completed**: YYYY-MM-DD
**Agent**:
**Result**:
**Deviations**:
**References**:
