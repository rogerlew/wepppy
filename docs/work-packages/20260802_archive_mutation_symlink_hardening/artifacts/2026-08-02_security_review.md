# Security Review - Run Archive Consistency and Symlink Hardening

## Metadata

- **Package**: `docs/work-packages/20260802_archive_mutation_symlink_hardening/`
- **Reviewer**: Pending independent security reviewer
- **Date**: Pending implementation review
- **Scope reviewed**: Pending contract checkpoint and implementation
- **Commit/branch context**: Pending

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: The package changes archive path traversal, cross-run
  symlink treatment, downloadable output, RQ coordination, and run-data
  integrity.
- **Threat model assumptions**:
  - Run trees may contain stale, malicious, relative, absolute, or cyclic links.
  - A participating mutation may remove or replace an entry at any traversal
    boundary.
  - Archive output must not disclose files outside contract-approved run scope.

## Required Review Surfaces

- [ ] Path normalization and run-root containment resist traversal and symlink
  escape.
- [ ] Cross-run link policy does not bypass source/target authorization or leak
  unrelated user data.
- [ ] Time-of-check/time-of-use replacement cannot turn an approved entry into
  an out-of-scope read.
- [ ] Lock ownership, TTL/renewal, ordering, cancellation, and recovery cannot
  create overlap, deadlock, or unauthorized force-clear behavior.
- [ ] Archive failures cannot publish partial ZIPs or leave stale temporary
  files, job identifiers, or coordination records.
- [ ] Queue retry/cancellation and RQ errors preserve canonical contracts.
- [ ] Restore behavior cannot write links or files outside the destination run.
- [ ] Logs provide actionable relative-path context without exposing unrelated
  absolute paths or secrets.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Pending | Pending | Pending | Review after contract checkpoint and implementation | Pending | Pending | Open |

## Verdict

- **Gate status**: `fail` (implementation has not been reviewed)
- **Unresolved findings**: pending
- **Release recommendation**: hold until review completion

## Validation Evidence

- Automated checks: pending.
- Manual generated ZIP and restore inspection: pending.
- Forest canary: pending.

## Residual Risk and Sign-off

- **Accepted residual risks**: none recorded.
- **Security reviewer**: pending.
- **Package owner**: pending.

