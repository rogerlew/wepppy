# Security Review - Frozen Topanga Census Execution

## Metadata

- **Package**: `docs/work-packages/20260809_peakflow_topanga_census_execution/`
- **Reviewer**: pending
- **Date**: 2026-08-09
- **Scope reviewed**: planned selection, filesystem, subprocess, concurrency,
  resume, aggregation, and retention surfaces
- **Commit/branch context**: `master`; execution not started
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
| SEC-EXEC-01 | High | Authorization gate | Full selection and execution wiring have not completed independent review | Active ExecPlan | Complete all preflight and review checkpoints before execution | Open |

## Verdict

- **Gate status**: `fail`
- **Unresolved findings**:
  - High: 1
  - Medium: 0
  - Low: 0
- **Release recommendation**: hold full-census execution

## Required Surface Checks

- [ ] Frozen plan ID and file hash match the preparation GO disposition.
- [ ] Selection contains exactly 1,088 unique eligible IDs and no excluded ID.
- [ ] Scenario authorities remain read-only, hash-matching, and symlink-safe.
- [ ] Evidence writes remain below the declared plan-specific root.
- [ ] Executable path and SHA-256 match the accepted observer.
- [ ] Worker count is bounded and each worker owns one isolated trial directory.
- [ ] Subprocess execution uses an argument vector with `shell=False`.
- [ ] Missing, stopped, failed, and complete terminals remain distinguishable.
- [ ] Retry preserves prior attempts and rejects binding mismatches.
- [ ] Aggregation validates all artifact hashes before reading content.
- [ ] No environment variable, shell text, or manifest field becomes a command.
- [ ] Logs and committed artifacts contain no secrets or unrelated file data.
- [ ] No routing, channel, network, queue, auth, CSRF, or public route surface is introduced.
- [ ] No new external dependency is introduced.

## Validation Evidence

- Automated checks: pending implementation and preflight.
- Manual selection, path, binary, concurrency, recovery, and retention checks:
  pending.

## Residual Risk

- **Accepted residual risks**: none while the gate is failing.
- **Follow-up packages/issues**: candidate adjudication and sampled routing are
  separate scopes and inherit no execution authority from this package.

## Sign-off

- **Security reviewer**: pending
- **Package owner**: requesting operator, package initiated 2026-08-09
