# Tracker - SURF-18 Pure UI DEVAL Loading Contract

## Status

Verified 2026-07-28 UTC.

## Progress

- [x] Registered SURF-18 after verified SURF-17.
- [x] Ratified the existing authorization, cache/enqueue, status, worker, and
  artifact contract.
- [x] Add direct render and executable inline-client evidence.
- [x] Add route, CAP, cache, enqueue, worker, artifact, and reload evidence.
- [x] Repair only confirmed conformance mismatches.
- [x] Complete security re-review and parent reconciliation.
- [x] Complete broad Python validation and records.
- [x] Prepared the atomic child commit and clean-worktree verification.
  reconciliation, commit, and clean closeout.

## Decisions

- CAP remains an abuse-control challenge and does not replace run
  authorization.
- Only the canonical `finished` job status is terminal success.
- Unknown, missing, and malformed polling states fail visibly rather than
  refreshing as if a report exists.
- Test SHR-03A-style lifecycle behavior as an encountered consumer without
  claiming the deferred shared package is complete.

## Conformance Classification

The package applies existing cross-cutting contracts from
`docs/schemas/rq-response-contract.md`,
`docs/schemas/rq-engine-agent-api-contract.md`, and the repository run-access
guardrails. Any confirmed authorization or status-classification mismatch is a
conformance defect under the unchanged contract, not intended new behavior.

## Outcomes

- Direct rendering and five executable inline-client tests cover identity,
  lifecycle, bounded retries, canonical terminal states, and escaped failures.
- Route and worker tests cover CAP plus run authorization, parent/PUP identity,
  cache and enqueue choices, owned-job reuse, confined artifacts, Docker/R
  execution, logs, status publication, and reload.
- Production repairs added missing run authorization, fail-closed status
  classification, generic transport errors, collision-resistant parent-owned
  PUP tracking, foreign-job rejection, CAP-before-context ordering, and symlink
  confinement.
- Focused validation passes 157 Python tests and 5 Jest tests. Full frontend
  validation passes 94 suites and 692 tests.
- Broad Python reached 2,462 passes and 40 skips before the known unrelated
  GridMET `_FakeUnits.degC` fixture failure.
