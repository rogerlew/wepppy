# Tracker - Recorder CSRF Transport Repair

## Quick Status

**Started**: 2026-08-23 20:35Z
**Current phase**: Complete
**Last updated**: 2026-08-23 20:44Z
**Next milestone**: Post-deployment Safari smoke confirmation.

## Task Board

### In Progress

- [ ] None.

### Done

- [x] Confirmed live failure response: HTTP 400 `csrf_failed` with detail
  `The CSRF session token is missing.`
- [x] Classified the repair as conformance to the unchanged canonical CSRF
  browser-client requirements.
- [x] Scaffolded package, tracker, and active ExecPlan.
- [x] Added browser transport and real Flask CSRF middleware regressions.
- [x] Replaced Beacon with credentialed, same-origin-only Fetch carrying
  `X-CSRFToken`, `keepalive`, and `mode: same-origin`.
- [x] Preserved singleton JSON event arrays in the recorder route.
- [x] Rebuilt the generated controller bundle and updated developer guidance.
- [x] Passed focused Jest 16/16, focused pytest 3/3, full frontend 773/773,
  full pytest 6,664 passed/63 skipped, npm lint, documentation lint, diff
  hygiene, and broad-exception enforcement.
- [x] Resolved security finding SEC-01 and obtained correctness/security passes.
- [x] Published closeout artifacts and synchronized package trackers.

## Decisions

### 2026-08-23: Preserve the existing CSRF policy

The recorder remains a cookie-authenticated Flask mutation route and therefore
remains CSRF protected. The repair changes only its browser transport; it does
not exempt the endpoint or weaken authorization.

### 2026-08-23: Reject cross-origin recorder endpoints before token discovery

An initial repair draft would have attached the CSRF header to an absolute
configured endpoint. The final implementation resolves and validates the
endpoint first and constrains Fetch to same-origin mode, preventing both direct
and redirect-based token disclosure.

### 2026-08-23: Preserve recorder JSON before shared normalization

The shared payload parser collapses singleton lists. The recorder route reads a
native JSON object first so a one-event `events` array remains an array, while
form compatibility continues through the shared parser.
