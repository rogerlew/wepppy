# Security Review - Frozen Topanga Census Execution

## Metadata

- **Package**: `docs/work-packages/20260809_peakflow_topanga_census_execution/`
- **Reviewer**: independent Codex security-review agent
- **Date**: 2026-08-09
- **Scope reviewed**: planned selection, filesystem, subprocess, concurrency,
  resume, aggregation, and retention surfaces
- **Commit/branch context**: `master`; generated execution evidence reviewed
- **Related artifacts**:
  - Code review: pending
  - QA review: pending
  - Scientific review: pending

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: full execution launches 1,088 local subprocess trials,
  writes a large content-addressed evidence tree, resumes prior attempts, and
  aggregates terminal artifacts.
- **Threat model assumptions**:
  - The CLI is used by an authorized local operator, not a public service.
  - The frozen plan and declared source authorities are untrusted until their
    hashes and path boundaries pass preflight.
  - Partial or malformed artifacts must fail closed and remain diagnosable.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-EXEC-01 | High | Authorization gate | Initial scaffold had no reviewed execution wiring | Initial active ExecPlan | Complete preflight and independent review before execution | Closed before launch after three HOLD/remediation cycles |
| SEC-EXEC-02 | High | Input integrity | Writable source authorities allowed drift after preflight | Independent interim review | Stage and hash every selected and shared input; validate again per trial | Closed by snapshot `2006d278...` |
| SEC-EXEC-03 | High | Concurrent ownership | Concurrent processes could own the same trial directory | Independent interim review | Add plan and trial `flock` ownership with no-follow lock creation | Closed and tested |
| SEC-EXEC-04 | Medium | Path handling | In-root redirects and malformed outside-boundary paths could redirect or hang | Independent interim review | Reject every symlink component and non-descendant before walking | Closed and tested |
| SEC-EXEC-05 | Medium | Subprocess availability | Observer had no timeout | Independent interim review | Add 300-second timeout and explicit stopped evidence | Closed |
| SEC-EXEC-06 | Medium | Immutable aggregation | Aggregation writes were raceable and incomplete | Final review | Share the plan lock, publish no-clobber, bind baseline, and inventory retained artifacts | Closed; final security revalidation PASS |
| SEC-EXEC-07 | Medium | Resume validation | Legacy complete reuse did not validate trace/pass hashes or reject unknown status | Final review | Validate reused artifacts and restrict retry to failed/stopped | Closed; final security revalidation PASS |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: security gate permits publication

## Required Surface Checks

- [x] Frozen plan ID and file hash match the preparation GO disposition.
- [x] Selection contains exactly 1,088 unique eligible IDs and no excluded ID.
- [x] Source reads and staged inputs are hash-matching and symlink-safe.
- [x] Evidence writes remain below the declared plan-specific root.
- [x] Executable path and SHA-256 match the accepted observer.
- [x] Worker count is bounded and each worker owns one isolated trial directory.
- [x] Subprocess execution uses an argument vector with `shell=False` and a timeout.
- [x] Missing, stopped, failed, and complete terminals remain distinguishable.
- [x] Retry preserves prior attempts and rejects binding, status, and artifact mismatches.
- [x] Aggregation validates terminal and baseline artifacts before reading content.
- [x] No environment variable, shell text, or manifest field becomes a command.
- [x] Logs and committed artifacts contain no secrets or unrelated file data.
- [x] No routing, channel, network, queue, auth, CSRF, or public route surface is introduced.
- [x] No new external dependency is introduced.

## Validation Evidence

- Automated checks: 18 focused host tests pass; canonical-container focused
  tests pass 17 with one environment skip. The canonical broad suite remains
  blocked by the documented `/tmp` ENOSPC condition.
- Manual and generated checks: 1,088 complete terminals; zero evidence symlinks;
  exact plan, selection, snapshot, executable, baseline, trace, and pass hashes;
  eight workers; 300-second timeout; shared plan/trial locks; immutable repeat aggregation.

## Authorization Chronology and Documentation Deviation

The independent interim reviewer returned three successive HOLD verdicts for
locking/path/environment, writable-authority/timeout/aggregation, and transformed
run-deck validation defects. Each was remediated and retested. At approximately
05:52 UTC, before the command recorded in `topanga-execution-manifest.json`
started, that reviewer explicitly issued GO: the staged full-execution regression
reached all fake-observer trials with zero stopped terminals and the sole final
blocker was closed.

This file was not synchronized from its initial failing scaffold to record that
live GO before launch. That is a procedural documentation defect, not an absent
review or silent risk acceptance. It is recorded here explicitly with the
review sequence and generated evidence preserved. Publication remained held
until independent final revalidation of all post-run hardening passed.

## Residual Risk

- **Accepted residual risks**: canonical broad pytest remains unavailable
  because `/tmp` is full; focused host and canonical-container evidence is retained.
- **Follow-up packages/issues**: candidate adjudication and sampled routing are
  separate scopes and inherit no execution authority from this package.

## Sign-off

- **Security reviewer**: independent Codex security-review agent; PASS after
  post-run hardening and provenance revalidation
- **Package owner**: requesting operator, package initiated 2026-08-09
