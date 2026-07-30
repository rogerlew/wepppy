# Tracker - SHR-06 Pure UI Command Bar Contract

## Status

Verified 2026-07-29 UTC.

## Progress

- [x] Registered and activated SHR-06.
- [x] Ratified the concise render, command, mutation, token, and agent contract.
- [x] Traced hosts, client lifecycle, Flask routes, shared helpers, and tests.
- [x] Added actual-render, direct-client, route, and hostile-content
  regressions.
- [x] Repaired only reproduced contract contradictions.
- [x] Ran focused, security, frontend, graph, repository, and docs gates.
- [x] Completed security review, reconciliation, and close.

## Decisions

- Keep safe viewer commands available; enforce authority independently at every
  state-changing backend route.
- Preserve command vocabulary, MCP token shape/TTL, agent TTL, and
  StatusStream protocol.
- Treat Project and agent routes as finite consumers only; do not broaden their
  registered packages.

## Validation

- Direct production Command Bar JavaScript: 1 comprehensive test passed.
- Focused shared JavaScript: 5 suites and 40 tests passed.
- Focused route/render Python: 198 tests passed.
- Frontend lint and full frontend: 104 suites and 739 tests passed.
- Test-stub and test-isolation gates passed.
- RQ dependency graph passed with 144 generated edges.
- Changed broad-exception enforcement and code-quality observability passed.
- Full repository Python: 5,570 tests and 12 subtests passed, with 58 skips.
- Child docs lint and `git diff --check` passed.
- Security review passed with no unresolved high or medium finding.
