# Tracker - Fork Destination Readiness Hardening

## Status

Closed as of 2026-07-29 21:36 UTC. Deployment was not performed.

## Task Board

- [x] Capture production evidence and freeze scope.
- [x] Discover and record prior fork/status hardening precedent.
- [x] Scaffold package and active ExecPlan.
- [x] Implement the readiness contract and exact regressions.
- [x] Run targeted and broad validation.
- [x] Complete independent code and QA reviews.
- [x] Close for operator-led local integration testing.

## Timeline

- **2026-07-29 20:51 UTC** – Fork job finished without exception; destination
  link initially returned HTTP 404 after the completion UI appeared.
- **2026-07-29 20:52–20:57 UTC** – Destination state and service health were
  verified on `wepp1`; the same URL later loaded without repair.
- **2026-07-29 21:16 UTC** – Hardening scope frozen and package scaffolded.
- **2026-07-29 21:36 UTC** – Local implementation, broad validation, and dual
  review completed; package closed without deployment.

## Decisions

- **2026-07-29 21:16 UTC** – Treat RQ completion and destination loadability as
  separate states. Rationale: the closed SURF-04 contract proves the former,
  while the incident disproves that it guarantees the latter.
- **2026-07-29 21:16 UTC** – Keep the change local and defer deployment.
  Rationale: the operator requested post-closure local integration testing.
- **2026-07-29 21:16 UTC** – Security impact is low. Rationale: the readiness
  check is read-only, binds the exact finished fork job and run IDs, and
  authorizes both runs; no auth, CAP, token, ownership, or mutation boundary is
  weakened.
- **2026-07-29 21:36 UTC** – Remove every pre-readiness destination anchor and
  disable cancellation once RQ success begins finalization. Rationale: neither
  alternate navigation nor a late cancel should bypass the readiness contract.

## Signal Snapshot

- Baseline: one confirmed transient post-completion HTTP 404 on one observed
  production fork.
- Post-change automated signal: delayed-readiness and exhaustion regressions
  prove that no destination anchor exists until readiness succeeds; all local
  gates passed.
- Post-deployment observation: deferred; owner is the WEPPcloud operator for
  14 days after any later deployment.

## Risks and Owners

- The exact production 404 access record was unavailable; shared-filesystem
  visibility is the strongest explanation, not a proven root cause. The
  operator owns post-closure integration evidence.
- Bounded retry timing must avoid hiding persistent failure. Codex owns explicit
  exhausted/error UI and deterministic tests.

## Validation

- `wctl run-pytest tests/weppcloud/routes/test_fork_console_route.py`: passed
  (final focused run: 11 tests).
- `wctl run-npm test -- console_smoke`: passed (27 tests).
- `wctl run-npm lint`: passed.
- `wctl run-npm test`: passed (104 suites, 743 tests).
- `wctl run-pytest tests --maxfail=1`: passed (5,572 passed, 58 skipped).
- Scoped documentation lint: passed.
- Changed-file broad-exception enforcement and `git diff --check`: passed.

## Review Disposition

- Independent code review: no unresolved medium/high findings. The initial
  early-link and unbound-readiness findings were fixed; stale documentation was
  corrected.
- Independent QA review: no unresolved medium/high findings. Initial cancel,
  auth/transport, and HTTP-boundary coverage findings were fixed.
- Remaining low-risk debt: real serialized-RQ-job coverage and behavior after
  the one-week job retention window. This does not weaken the immediate
  post-completion incident fix; an expired manual retry fails visibly.
