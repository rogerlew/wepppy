# Tracker: Fork Option Availability and Readiness

Timezone: UTC. Updated: 2026-10-08 00:05 UTC.
Base: `918b3ca0a1639c0ec057decbf4fd1b6bac25b10b`.
Phase: complete for code/local validation and read-only predicate replay.
Production deployment remains separate. Accepted checkpoint ancestor:
`b80235d8fcf15ab682bdae248171b5305802dea2`.

## Progress

- [x] Diagnose all three affected forks from wepp1 logs, RQ, and filesystem.
- [x] Draft capability/readiness contract, decision, and execution plan.
- [x] Operator accepted the concrete checkpoint, checkpoint commit, two
  independent reviewer agents, and implementation on 2026-10-07 UTC.
- [x] Independent correctness/security reviews passed and checkpoint committed.
- [x] Implement and document the bounded change; focused and frontend tests pass.
- [x] Independent correctness/QA and security reviews pass without findings.
- [x] Candidate readiness passes all three incident destinations in read-only
  wepp1 replay under uid 1002 / gid 130; original deployed helper remains false.
- [x] Full Python suite: 10,418 passed, 126 skipped.

## Decisions and findings

The UI restrictions do not replace backend no-op compatibility. Distinguish
unused/empty Omni from configured or retained scenario/contrast state. Preserve
strict checks on existing controllers and unsafe filesystem entries.
All additional details and rationale are in the draft current contract.

The operator explicitly approved the checkpoint, reviewers, and implementation
on 2026-10-07 UTC. No production action is included.

## Validation

Focused route/render tests: 118 passed. Frontend: 113 suites / 924 tests passed.
Frontend lint, documentation lint, broad-exception enforcement, and diff checks
pass. Controller bundle rebuild produced no generated diff. Full Python suite:
10,418 passed, 126 skipped. Final review and validation artifacts are in `artifacts/`.
Read-only production replay is not evidence that the web fix is deployed.
