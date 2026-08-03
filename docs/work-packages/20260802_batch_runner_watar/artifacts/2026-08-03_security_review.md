# Security Review - Batch Runner WATAR Integration

## Metadata

- **Package**: `docs/work-packages/20260802_batch_runner_watar/`
- **Reviewer**: pending independent security reviewer
- **Date**: pending
- **Scope reviewed**: planned Batch Runner WATAR directive, worker execution,
  retry classification, run-tree writes, locking, and any RQ dependency changes
- **Commit/branch context**: pending implementation revision
- **Related artifacts**: contract checkpoint and correctness review pending

## Security Triage Decision

- **Security impact level**: high.
- **Dedicated security review required**: yes.
- **Triage rationale**: the package changes an expensive worker path, retry and
  completion decisions, run-scoped file generation, locking, and possibly RQ
  dependency edges. It must preserve existing admin/JWT boundaries.
- **Threat model assumptions**:
  - Only the existing authorized Batch Runner and WATAR entry points can mutate configuration or enqueue work.
  - Batch leaf identifiers and paths remain inside the validated batch run root.
  - WATAR consumes only run-scoped state and approved configured resources.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Pending | Pending | Pending | Review after implementation scope is fixed. | Pending | Pending | Open |

## Verdict

- **Gate status**: fail (review not yet performed).
- **Unresolved findings**: high/medium/low counts pending.
- **Release recommendation**: hold until the review is complete and all
  medium/high findings are resolved.

## Required Surface Checks

- [ ] Existing Batch Runner admin/JWT and CSRF boundaries are unchanged.
- [ ] `run_watar` directive and stored inputs cannot escape batch/run scope.
- [ ] Worker inputs and paths are validated before file or subprocess work.
- [ ] WEPP-before-WATAR ordering and failure propagation are deterministic.
- [ ] Retry/cancellation cannot bypass ownership checks or clear active locks.
- [ ] NoDb and NoDir lock/persistence contracts are preserved.
- [ ] RQ graph and live job-tree evidence match intended edges.
- [ ] Logs aid triage without exposing secrets or sensitive inputs.
- [ ] Rollback and containment are documented and tested.

## Validation Evidence

Pending implementation and review. Required evidence is enumerated in
`prompts/active/batch_runner_watar_execplan.md`.

## Residual Risk

- **Accepted residual risks**: none accepted.
- **Follow-up packages/issues**: pending review.

## Sign-off

- **Security reviewer**: pending.
- **Package owner**: pending.
