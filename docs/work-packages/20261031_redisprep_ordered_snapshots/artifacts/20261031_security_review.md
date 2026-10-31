# Security review — RedisPrep snapshots

Reviewer: independent `security_implementation`; contract reviews by
`contract_security`. Date: 2026-10-31 UTC. Scope: filesystem publication,
namespace/restore boundaries, effective access and coordination. Ancestors:
88b5c174f / ea95e1298; implementation working tree.

## Triage and assumptions

High impact because shared filesystem/path restoration changed. No new auth,
privilege, dependency, queue topology, network service or secret handling.
Existing project access and runtime identities remain authoritative. Healthy
readers, empty/fresh state, legacy snapshots and incoming archive modes must
continue to work. Local modes do not establish full cross-host ACL parity.

## Findings

| ID | Severity | Surface | Disposition |
| --- | --- | --- | --- |
| SEC-01 | High | Failed restore cleanup could overwrite committed incoming bytes | Resolved: no stale snapshot publication after destructive failure; late-failure regression |
| SEC-02 | Medium | Loaded 0555 reader required new mkdir access | Resolved: write-free healthy path; real UID1000 test |
| SEC-03 | Medium | Fork lost 0600 policy; archive exposed private data under old mode | Resolved: explicit staging modes before replace |
| SEC-04 | Medium | NFS replace response error incorrectly asserted prior bytes retained | Resolved: attempted replace is uncertain (`published=None`); replace-then-error test |
| SEC-05 | High, contract phase | Killed restore could erase replacement provenance | Resolved: durable pre-destructive fence retained through extraction, copied markers ignored |

Incremental review also approved namespace revalidation, root-only live archive
activation, serializer/lifecycle lock ordering, stable lock-inode retention and
batch/latest guards. No medium/high code findings remain.

## Evidence and verdict

49 real Redis/process/filesystem cases passed on the NFS client under UID1000/
GID993. The suite covers mode-0555 reads, first-create umask, preserved replacement
mode, fork root/snapshot symlinks, archive staging mode and retained failure bytes.
`access.jsonl` records real service-identity read/write/readback. No production
job or host mutation occurred. Scientific parameters and auth are unchanged.

Verdict: approved for local code delivery, **rollout hold** pending representative
cross-host NFS/local-server exclusion, configured physical aliases and ownership/
group/ACL parity. Single-client NFS and same-host containers do not prove those
boundaries. Operator accepted only the documented historic partial-loaded-state
reconciliation limit; no broader risk waiver is inferred.
