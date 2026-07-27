# WP04 — CSRF-Enabled Same-Origin Test Matrix

> **Purpose**: Add integration tests that actually exercise the same-origin/CSRF decision table across all three guards, including the header combinations that unit fixtures skip.
> **Target**: Codex
> **Created**: 2026-07-27
> **Status**: Active
> **Security gate**: Part of a `high`-triage package; this WP is the regression backstop the security review relies on.

## Context

Independent-review finding 1 recommended durable CSRF-enabled integration coverage of the anonymous origin/header matrix; the current route unit fixtures do not initialize `CSRFProtect`, so the CSRF-plus-same-origin interaction is unverified. WP01 unifies three guards to one contract — that contract needs a shared matrix asserting each guard behaves identically.

- Current state: guard behavior covered piecemeal; CSRF interaction and the full header matrix not exercised.
- Goal state: one shared matrix, applied to all three surfaces, run in CI.

## Objective

For each of the three guards (Flask reset endpoint, rq-engine cookie-authenticated route, query-engine bandwidth upload), assert the WP01 decision table over the full input matrix, with CSRF enabled where the surface enforces it.

**Success looks like**: any future regression that weakens or diverges a guard fails a test.

## Working Set

### Files to Read (Inputs)
- The WP01 contract section in `docs/schemas/weppcloud-csrf-contract.md` (decision table + shared vectors).
- The three guards and their existing tests: `tests/weppcloud/routes/test_rq_engine_token_api.py` (reset), the rq-engine session-route tests, and the query-engine bandwidth tests.
- Existing test harness/fixtures, including how (or whether) `CSRFProtect` is initialized in route tests.

### Files to Modify (Outputs)
- The three test suites (or a shared parametrized helper) — add cases: valid same-origin token; absent token (expect the surface's CSRF failure); missing `Origin` AND `Referer`; `Origin: null`; scheme mismatch; port mismatch; subdomain mismatch; `Sec-Fetch-Site: same-origin` with a conflicting `Origin` (expect reject); `Sec-Fetch-Site: cross-site` (expect reject); `Sec-Fetch-Site: same-origin` with `X-Forwarded-Proto: http` while Origin is https (expect accept — the bearhive case).
- Test fixtures — initialize `CSRFProtect` where the surface enforces CSRF so the token path is actually exercised.

### Files to Avoid (Exclusions)
- Guard implementations (WP01 owns those) — this WP only adds tests, unless a test surfaces a contract violation to route back to WP01.

## Instructions
1. Encode the WP01 decision table as shared vectors (ideally parametrized so all three suites consume the same cases).
2. Ensure CSRF is enabled in the relevant fixtures; assert both the token requirement and the same-origin decision.
3. Include the bearhive-topology case explicitly (same-origin accepted despite `X-Forwarded-Proto: http`).
4. Assert cross-origin/`Origin`-conflict cases reject on every surface.

## Validation Gates
- `wctl run-pytest` for all three suites.
- `wctl run-npm lint` / `wctl run-npm test` (if any JS test is touched).

## Deliverables
1. Shared same-origin/CSRF matrix applied to all three guards.
2. CSRF-initialized fixtures.
3. Green suites proving parity.

## Handoff Format
Report per the tracker's Progress Notes convention; include the vector table and per-surface pass counts.

---

## Outcome (Complete this when retiring the prompt)

**Completed**: YYYY-MM-DD
**Agent**:
**Result**:
**Deviations**:
**References**:
