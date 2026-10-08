# FORK-UI-01 Security Review

Reviewer: `/root/fork_contract_security`, independent `security_reviewer` role.
Reviewed: 2026-10-07 23:23 UTC. Context: implementation after `b80235d8f`.
Authority: current fork-console contract and its shared contracts.
Security impact: high (review classification, not a finding severity).

## Verdict

PASS. No unresolved findings. SEC-C01 remains closed. Review was read-only and
followed correctness/QA approval. No deployment action or approval is implied.

## Surface checks

| Surface | Evidence and disposition |
| --- | --- |
| Source capability inspection | Plain JSON, no executable decoding, controller hydration, migration, or source writes |
| Metadata filesystem entries | NOFOLLOW and NONBLOCK, regular-file validation, finally-close on all exits; symlink, dangling link, directory, FIFO, and malformed data tests |
| Legacy source behavior | Real flat/py-state fixtures without nodb.version; full source byte/path snapshot unchanged |
| Legitimate SBS artifacts | Source/derived/absolute/linked map compatibility preserved |
| No-controller readiness | Only absent or real empty optional directories accepted |
| Existing Omni controller | Still requires complete empty real directory structure |
| Hostile/unreadable destination | Symlinks, special entries, non-directory ancestors, populated state, and access failures remain false |
| Authorization and lifecycle | Source/destination checks, exact fork binding, finished status, and core checks unchanged |
| Disabled UI | Native disabled markup, help association, false serialization, stale query/bootstrap and restored-job tests |
| Job/API/worker boundary | No producer, worker, job-argument, API-acceptance, or queue changes |

## Evidence reviewed

The parent reported final focused results of 118 passing Python tests and
924 frontend tests plus lint. The independent correctness/QA reviewer confirmed
the last descriptor-cleanup and combined restored-job coverage changes.
Read-only wepp1 replay under uid 1002 / gid 130 validates the predicate on all
three real destinations without modifying their core files; identities and
hashes are retained in the validation artifact.

## Residual limits

Readiness remains a filesystem snapshot, not model-output certification. The
full Python gate is pending at review time and must be recorded before handoff.
Production endpoint and UI recovery require separate deployment acceptance.
