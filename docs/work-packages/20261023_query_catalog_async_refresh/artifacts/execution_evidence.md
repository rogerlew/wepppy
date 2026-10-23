# Execution evidence ledger

Status: scaffold only, 2026-10-23 UTC. Contract ancestor: `dc2b2ddbe8cfedbd4bae024310f03447ca813c32`. No implementation evidence yet. Populate each row with exact revision, command/environment, observed semantic result and retained artifact path. Pending is not passed.

| Gate | Required evidence | Status |
| --- | --- | --- |
| M0 source/authority | Ancestor check; current caller/native drift; root/consumer map; nearest guidance | Pending |
| M1 atomic publication | Concurrent sync/async readers/writers; digest/status crash points; full/subtree parity | Pending |
| M1 lifecycle/NFS | Cross-host guard exclusion, lock order, restore/delete/recreate stale worker, standalone wrong-mode | Pending |
| M1 native | Actual traversal heartbeat with GIL released; native output/schema parity; paired build provenance | Pending |
| M2 durable requests | Real Redis duplicate/WATCH/ambiguous transaction cases; receipt replay and partial failure | Pending |
| M2 no lost updates | During-scan/final-check arrivals, worker death, Redis loss, no-worker recovery | Pending |
| M2 receipt-free gap | Kill after artifact publication before invalidation; convergence without another request | Pending |
| M2 capacity | Worker compatibility and bounded cycle/admission; oldest unreconciled scope and queue delay | Pending |
| M3 reader freshness | Existing membership with changed schema/alias/fs_path; context reload; actual query/report values | Pending |
| M3 disclosure | Single/batch/recursive/status/info/missing/import-failed/abandoned/rollback redaction | Pending |
| M3 finalizers | No same-queue self-deadlock; completion only after required catalog readback | Pending |
| M4 incident | Isolated Mill Creek copy; responsive submission, actual job/model artifacts and immediate report | Pending |
| M5 family migration | Each A/A-C matrix row has revision/evidence or explicit retained-sync disposition | Pending |
| Visibility/archive | Authorized browse/download; exact archive members, bytes/modes, new restore incarnation | Pending |
| READONLY | Generic refusal plus positive manifest-owned combined-viewer preparation/rollback | Pending |
| Regression | Focused/broad gates, stub/frontend if changed, queue graph and live job tree | Pending |
| Independent review | Correctness/security review artifacts, finding dispositions, post-fix confirmations | Pending |
| Rollout | Separately authorized deployment, exact Python/native versions and real workflow evidence | Not authorized by scaffold |
| Repair | Separately authorized affected-project recovery and final consumer readback | Not authorized by scaffold |

## Completion claims

- Contract specified/reviewed/committed: yes.
- Execution scaffold committed: record in tracker after scaffold commit.
- Implemented / locally validated / environment validated: no.
- Deployed / production repaired / incident resolved: no.

## Run log

Append UTC milestone entries here with commands and references. Do not store credentials, raw tokens or unnecessary personal data. Keep useful failure evidence visible under the contract's project artifact paths during actual execution.
