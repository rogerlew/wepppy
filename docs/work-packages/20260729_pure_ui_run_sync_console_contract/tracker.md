# Tracker - SURF-05 Pure UI Run Sync Console Contract

## Status

Closed 2026-07-29 UTC.

## Progress

- [x] Registered and activated SURF-05.
- [x] Ratified the concise render/client/API/RQ/filesystem contract.
- [x] Traced route, template, source/generated client, API, worker, and tests.
- [x] Added exact actual-render and eight direct real-client regressions.
- [x] Repaired the reproduced duplicate-submission window.
- [x] Ran focused, security, frontend, graph, and repository gates.
- [x] Completed security review, parent reconciliation, and close.

## Decisions

- Preserve the current fields, booleans, Admin boundary, source-token Redis
  handoff, migration dependency, target-root default, and worker semantics.
- Treat deferred shared packages only as consumer evidence reached by SURF-05.
- Require one active browser submission owner without changing backend queue
  topology or adding a new cross-process exclusion contract.

## Validation

- Direct Run Sync controller: 1 suite, 8 tests passed.
- Render/route/generated-bundle wiring: 166 tests passed.
- Run Sync API/RQ/migration worker: 10 tests passed.
- Security-focused auth/lifecycle/logging: 17 tests passed.
- Frontend lint passed; full frontend: 102 suites, 735 tests passed.
- `wctl check-rq-graph` passed.
- Repository Python: 5,559 tests passed, 58 skipped.
- Child/umbrella/project documentation lint, spelling preview, generated-bundle
  wiring, and `git diff --check` passed.
