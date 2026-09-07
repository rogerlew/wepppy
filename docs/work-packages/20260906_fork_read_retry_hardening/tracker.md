# Tracker: FORK-READ-01

## Status

2026-09-07 UTC: Scaffolded; preparing contract checkpoint before implementation.
Starting revision: `87cfe40473108a93cbbd5733fdc13c99d97707ea`.

## Task Board

- [x] Capture incident and operator burst-of-small-files hypothesis.
- [x] Discover NoDb, fork, deferred retry and serial-queue precedents.
- [ ] Two independent contract reviews; standalone contract ancestor.
- [ ] Implement bounded reads and diagnostics.
- [ ] Implement fork prerequisite failure reporting.
- [ ] Validate filesystem/RQ integration, focused/broad suites and graph.
- [ ] Independent correctness, QA and security reviews; documentation handoff.

## Decisions

- 2026-09-07 UTC: ENOENT and ESTALE only; 5-second total read-context budget,
  0.1-second initial exponential delay capped at 1 second. No write/job retries.
- 2026-09-07 UTC: Initial preparation controller reads opt in; ordinary web
  loads retain immediate errors and optional absence retains None semantics.
- 2026-09-07 UTC: Failure callbacks report terminal child failure; they do not
  cancel sibling jobs, release active claims or run blocked model stages.

## Validation and Risks

Pending implementation. A hard-mounted NFS syscall can block beyond a Python
retry deadline; this package bounds retry scheduling, not kernel I/O duration.

## Handoff

Active plan: [ExecPlan](prompts/active/fork_read_retry_hardening_execplan.md).
