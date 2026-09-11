# Security review — batch task boundary

## Metadata and triage

Reviewer: `/root/contract_security` (independent read-only security reviewer),
2026-09-11. Source baseline `0c34afdb5`; approved contract ancestors `869ca7dcf`
and `f221e7f2a`. Impact: high, because queue wiring and shared-run mutation change.
Scope: stage lineage, receipt publication/validation, cache ownership, worker
identity/logging and finalizer integrity. No auth, privilege or service expansion.

## Findings

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| SEC-01 | Medium | Required identity records could expire before delayed consumer | Resolved: root/hillslope result TTL -1, with real Redis assertions |

Contract findings CS-01/CS-02 were resolved before production implementation;
see the standalone contract review artifact.

## Surface checks

- Invalid task identity/foreign lineage fails before run-tree writes, including
  the terminal metadata handler. Worker prevalidation logging is deferred for
  exactly these tasks.
- Valid-leaf bad receipts produce explicit failure, without watershed/Omni
  mutation. Receipt identity, upstream success and RQ mirror must agree.
- Real filesystem publication failure retains scientific outputs; symlink
  receipt/controller escape cases are rejected.
- Real NoDb/Redis tests preserve foreign lock ownership and unrelated cache;
  optional absent Ash remains valid. No stage-two lock clearing was introduced.
- Real RQ tests cover root failure/retry, cancellation, mixed leaves, concurrent
  Omni and pending-link failure suppression. Explicit operator recovery for
  incomplete Omni linkage is documented; manual flag-clearing is prohibited.
- Canonical archive/restore tests preserve visible handoff bytes in working,
  failed, successful and restored states.

## Verdict

Implementation findings closed; zero unresolved high/medium security findings.
Full-suite and live Forest browser/download identity evidence remain package
acceptance gates. The reviewer inspected code/tests and primary-agent reports;
they did not independently rerun tests. Receipt mode is 0600; live readability
under the shared Compose service UID must be recorded before package closure.
