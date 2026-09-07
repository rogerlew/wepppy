# Security Review — FORK-READ-01

## Metadata

Reviewer: independent `contract_security` security reviewer, 2026-09-07 UTC.
Scope: NoDb read retries, fork child association, atomic Redis failure
publication, and worker supervisor fallback following ancestor `2ad307aeb`.
Author recorded the returned review. Related artifacts:
[correctness](2026-09-07_correctness_review.md) and [QA](2026-09-07_qa_review.md).

## Security Triage Decision

High: filesystem reads and worker callback state changes warrant dedicated
review. Assumptions: Redis/RQ is a trusted internal service; existing run
resolution and enqueue authorization remain authoritative; STATUS and RQ use
the same Redis server. No new external service, auth surface or dependency.
Valid required, optional, populated, absent and legacy states follow the
correctness matrix; controls must not return stale cache or reject normal
optional absence.

## Findings

| ID | Severity | Surface | Disposition |
| --- | --- | --- | --- |
| SEC-01 | Medium | Optional file disappearance during signature validation | Resolved: optional ENOENT reaches all signature/read paths and returns None without retry or stale cache; direct disappearance regressions added |

## Surface Checks

- Auth/session/CSRF, secrets, external network, MCP and CI/CD surfaces unchanged.
- File reads use existing run/controller paths; writes, locks, path resolution
  and deserialization policy are not broadened. Retry scope does not encompass
  translation, input generation or whole jobs.
- Callback authority comes from fetched root function, queue, args, registered
  child ID and target, not child metadata alone. Lua checks receipt and planned
  source/target/root identity before atomically storing and publishing failure.
- Foreign linkage, receipt replacement between validation and commit, missing
  lineage, legacy jobs, duplicate callbacks and succeeded state cannot publish.
- Strict dependencies and active claims are unchanged. The supervisor fallback
  uses the same guarded reporter and catches Redis status-refresh errors.
- Original task errors survive reporting failures. Public source status contains
  a generic explanation and child ID; errno/paths stay in operator diagnostics.
- Retry contexts are isolated, finite and back off; optional absence is not
  retried. EACCES/EPERM/EIO/ENOTDIR/ELOOP and other non-allowlisted errors remain
  immediate failures. Redis and write operations are not retried.

## Validation Evidence

Reviewer verified checkpoint ancestry, implementation, whitespace checks and
228 passing focused tests, including actual filesystem recovery, actual
Redis/RQ callbacks and hostile association checks, and real work-horse death.
Correctness and QA independently accepted before final security sign-off.
Broad validation and graph/stub checks are recorded in the validation artifact;
security approval does not substitute for those gates.

## Verdict and Sign-off

PASS for local implementation. Independent security reviewer confirmed no
unresolved high, medium or low findings. Author/package implementer: Codex.
Production rollout remains on hold for actual fork/undisturbify evidence under
production-equivalent identities, mounts and orchestration. A hard-NFS syscall
may outlive the application retry deadline; NAS recovery is not proven by
injected ESTALE or local publication tests.
