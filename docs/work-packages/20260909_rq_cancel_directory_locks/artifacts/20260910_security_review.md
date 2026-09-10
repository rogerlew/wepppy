# Security review: RQ cancellation directory locks

## Metadata and triage

Reviewer: /root/cancel_impl_security, 2026-09-10 UTC.
Checkpoint ancestor: 3903cb778. Security impact high; dedicated review required.
Scope: process termination and directory lock ownership/release. Auth, CSRF,
enqueue topology, NoDb controller locks and production deployment are unchanged.

Threat assumptions: a dedicated Linux RQ supervisor executes one workhorse at a
time; the installed RQ scheduler performs Redis scheduling without spawning
writers. Execution identity is server-created before fork, not read from request
or job metadata. Unknown preexisting children prohibit cleanup.

Valid absent, empty, populated and legacy states follow the correctness matrix.
Pidfds prevent signals to recycled PIDs. Detached/reparented writers are adopted
by the supervisor. Scheduler death or unavailable process inspection retains
locks. A previous execution's live writer cannot become a later job's property.

## Findings

| ID | Severity | Surface | Required action and evidence | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | High | Missing live-task children interface treated as no children | Explicit error when live task lacks inspection; no-release regression | Resolved |
| SEC-02 | Medium | Metadata WATCH/Redis errors skipped local termination | Log diagnostic errors independently; real detached-writer fault scenarios | Resolved |

Reviewer independently confirmed both fixes and no new medium/high findings.
Execution UUID plus job ID and atomic full-payload comparison preserve unrelated,
legacy, replacement and same-job retry locks. Broad Redis scanning is a scaling
concern, not a confirmed authorization bypass.

## Surface checks and evidence

No new credentials, auth scopes, endpoints, shell commands, or payload authority.
Redis access uses existing secret-file configuration. Cleanup logs job/execution
identity and root keys without credentials. The real worker-container probe at
2026-09-10 04:29:35 UTC used UID 1000, GID 993, groups [993], umask 0022 and the
/wc1/runs mount. Job 7ef2c606-1e8c-4378-88ee-75b974756a5b stopped inherited and
detached writers, cleared three owned locks, and immediately reacquired climate.
Its scheduler, unrelated writer and legacy landuse lock survived. Test resources
were removed. See 20260910_validation.md.

## Verdict and sign-off

Gate: pass; no unresolved high/medium findings.
Reviewer approval covers the local implementation and reported development
worker evidence. A subsequent actual WorkerPool probe at 04:42:36 UTC also passed under the same
worker identity/run mount (job 637ea73a-4394-4dbc-8ef4-df406b76d3ac).
Full-suite validation completed: 8202 passed, 83 skipped; final focused suite 17 passed. No production rollout
was reviewed or authorized. Legacy locks and whole-container crashes retain
existing operator recovery.
