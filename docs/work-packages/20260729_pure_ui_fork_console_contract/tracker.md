# Tracker - SURF-04 Pure UI Fork Console Contract

## Status

Closed 2026-07-29 UTC.

## Progress

- [x] Registered SURF-04 after SURF-01 and verified shell/domain dependencies.
- [x] Ratified the concise render/client/API/RQ/recovery contract.
- [x] Reconciled the completed fork-copy predecessor without changing evidence.
- [x] Added exact actual-render and executable fork-client regressions.
- [x] Ran authorization, CAP, API, cancellation, worker, and terminal evidence.
- [x] Confirmed no production mismatch required repair.
- [x] Completed broad validation, security review, parent reconciliation, and
  close.

## Decisions

- Preserve current fork booleans, CAP/auth alternatives, scoped sessionStorage,
  authoritative polling, bounded StatusStream thresholds, cancellation, copy,
  and identity-normalization behavior.
- Treat SHR-02 and SHR-03A only as consumer evidence reached by SURF-04; do not
  advance either deferred shared owner.
- Consume the old fork-copy package's backend evidence and close its deferred
  route-to-client default-propagation gap here.

## Validation

- Focused real console Jest: 1 suite, 15 tests passed.
- Fork route/render/template/stale wiring: 168 tests passed.
- Fork/cancel API and RQ worker: 89 tests passed.
- Security-focused cross-service/CAP/logging: 29 tests passed.
- Frontend lint passed; full frontend: 101 suites, 719 tests passed.
- Repository Python: 5,555 tests passed, 58 skipped.
- Documentation lint and `git diff --check`: required at closeout.
- `wctl check-rq-graph`: existing static artifact drift; no SURF-04 queue
  wiring changed.
