# WP04 — Shared Same-Origin Matrix and Surface Security Tests

> **Purpose**: Apply one origin-predicate matrix to all three guards and verify
> each surface's distinct outer security controls.
> **Target**: Codex
> **Created**: 2026-07-27
> **Status**: Active
> **Security gate**: Part of a `high`-triage package; this WP is the regression backstop the security review relies on.
> **Hard dependency**: WP00-WP03 must be complete, and the WP00 checkpoint
> revision must be an ancestor of `HEAD`.

## Context

Independent-review finding 1 recommended durable integration coverage of the
origin/header matrix. Flask route unit fixtures do not initialize
`CSRFProtect`, so Flask-WTF interaction is unverified. WP01 unifies three guard
predicates; outer security layers remain surface-specific.

- Current state: guard behavior covered piecemeal; CSRF interaction and the full header matrix not exercised.
- Goal state: one shared matrix, applied to all three surfaces, run in CI.

## Objective

Apply one shared pure origin-decision vector set to the three guard predicates.
Separately test each surface's outer control: Flask-WTF CSRF on reset,
cookie/session authentication on rq-engine, and the existing anonymous/rate
limit boundary on query-engine. Do not require identical final HTTP status when
an outer layer rejects first.

**Success looks like**: any future regression that weakens or diverges a guard fails a test.

## Working Set

### Files to Read (Inputs)
- The WP01 contract section in `docs/schemas/weppcloud-csrf-contract.md` (decision table + shared vectors).
- The three guards and their existing tests: `tests/weppcloud/routes/test_rq_engine_token_api.py` (reset), the rq-engine session-route tests, and the query-engine bandwidth tests.
- Existing test harness/fixtures, including how (or whether) `CSRFProtect` is initialized in route tests.

### Files to Modify (Outputs)
- The three test suites (or a shared parametrized helper) — add pure guard
  cases for missing signals, `Origin: null`, scheme/port/subdomain mismatch,
  conflicting Origin, cross-site, raw forwarded-header non-authority, and the
  exact HTTP:80 application tuple to HTTPS:443 same-host bridge.
- Test fixtures — initialize `CSRFProtect` where the surface enforces CSRF so the token path is actually exercised.

### Files to Avoid (Exclusions)
- Guard implementations (WP01 owns those) — this WP only adds tests, unless a test surfaces a contract violation to route back to WP01.

## Instructions
0. Verify the tracker records the WP00 checkpoint revision and WP01-WP03
   completion. Stop if the checkpoint is not an ancestor of `HEAD`.
1. Encode the WP01 pure guard decision table as shared vectors consumed by all
   three predicates.
2. For Flask only, initialize `CSRFProtect`, obtain a real token by entering a
   request context and calling `generate_csrf()`, preserve the test-client
   session cookie, and send the token header. Assert valid, missing, and invalid
   tokens. When CSRF and origin are both invalid, expect Flask-WTF's CSRF
   rejection because global middleware runs before the route predicate.
3. For rq-engine, test cookie/session authentication separately from the guard.
   For query-engine, preserve its existing anonymous and rate-limit assertions;
   neither surface gains Flask-style CSRF.
4. Model the bearhive topology through each framework's authoritative request
   URL/Host fixture as HTTP:80 plus an HTTPS:443 same-host Origin. Do not use
   `X-Forwarded-Proto` to create the application tuple.
5. Prove raw forwarded headers, including the enabled legacy rq-engine switch,
   cannot add an allowed origin.
6. Assert host/subdomain/explicit-port conflicts reject on every predicate.

## Validation Gates
- `wctl run-pytest` for all three suites.
- `wctl run-npm lint` / `wctl run-npm test` (if any JS test is touched).

## Deliverables
1. Shared pure same-origin matrix applied to all three guards.
2. Per-surface CSRF/auth/boundary fixtures and assertions.
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
