# October 26 rollout gate disposition

Status: **HOLD — production async remains disabled.** Completing the checks does
not authorize treating failed or unmeasured acceptance conditions as passed.

## Passed evidence

- Full fresh local scientific and consumer acceptance: 18 finished jobs, 1,908
  hillslopes, 184 years, 128,227,140 complete unique daily observations, strict
  reports and authenticated exact-byte downloads; zero pending receipts. See
  [terminal acceptance](20261026_resumed_acceptance.md#terminal-acceptance-and-remaining-rollout-scope).
- Actual production uid1002/gid130, existing batch container and NFS: copied 79
  real Parquet tables (73,328,103 bytes) into an isolated flat managed namespace.
  Receipt-free discovery admitted a real RQ refresh and completed the cycle in
  6.955 s using SimpleWorker; repeat with normal forking RQ Worker passed in
  7.762 s. Catalog contained all 79 selected tables (80 total entries), zero
  receipts remained, and all selected source/copy row counts matched. Sources
  were read only; no production job or existing project was modified.
  [Cycle](20261026_rollout_cycle.json), [forking worker](20261026_rollout_workhorse.json),
  [table readback](20261026_rollout_readback.json).
- Cross-host exclusion and worker heartbeat: all 29 probe processes passed;
  no guard inode replacement, mount adjustment or permission change.
  [Independent lock review](rollout-lock-acceptance.md).
- Candidate four-namespace configuration parses identically on all three hosts
  (configuration SHA256 `02d605c5c8a13a1210ac866e879cb38fff5d6afbb04d8e73e394a28a8c23c2f8`).
  This was process-local parsing/access verification, not persistent fleet
  configuration or enabled-worker registration.
  [Candidate root parity](20261026_candidate_root_parity.json).

## Conditions that prevent enablement

1. **Owned namespace coverage.** The three-root example omits active, owned legacy
   projects under `/geodata/weppcloud_runs`. Explicit configuration must include
   that namespace and shared `/wc1/query-engine-coordination/locks`. Its mount is
   read-only on wepp3: validate that participant's actual fork/archive role,
   without assuming a need or authorization to change mount permissions.
2. **Full inventory and capacity.** A representative cycle is not a complete fleet
   cycle. The legacy inventory probe has exceeded the 60 s lease without a
   checkpoint; name-only enumeration also stalls before child metadata checks.
   A full streaming `scandir` attempt also exceeded 60 s: 10,000 entries
   consumed 33.535 s, then the probe timed out before completion. Its first 100
   entries took 0.115 s, illustrating why small warm samples cannot certify the
   full directory. Retain diagnostics and establish resumable progress before certifying the
   24-hour target. Raising a lease or dropping legacy roots is not an evidenced
   solution. Full counts, oldest unreconciled age and full-cycle duration remain
   unproved.
3. **Request readiness under contention.** Measured lock waits reached 30.5 s,
   with publication up to 35.4 s. Python heartbeats remained healthy, but deployed
   async HTTP handlers call synchronous freshness barriers on their event loop.
   This is a conditional request/readiness exposure, not an observed live outage.
   Validate bounded HTTP contention and isolate blocking work from the event loop
   before claiming request responsiveness.

Primary-root discovery stopped with a retained checkpoint after 46 completed
ticks: 4,600 nodes, 2,735 candidate scopes (2,192 top-level/543 nested), 705.68 s
scanning, maximum completed tick 42.88 s and no observed lease overruns. Another
125 nodes remained on the stack, including 121 shards. These are incomplete
counts, not a fleet inventory or full cycle. See the inventory artifacts for
[raw timing, cursor hashes and termination evidence](20261027_rollout_inventory.json).
All owned inventory diagnostics exited; retained scratch evidence remains.

Shared batch historical sample: 169 retained finished jobs, median service
5,173 s, p95 9,370 s, maximum 48,194 s; median enqueue-to-start 0.081 s, p95
0.307 s, maximum 5,226 s. Finished-job retention and survivor selection limit
this sample; it cannot guarantee capacity for fleet-wide maintenance. Controlled
canaries use a unique temporary queue and compatible test worker, not shared
batch scheduling under added maintenance load.

## Operational decision

Keep `QUERY_CATALOG_REFRESH_ENABLED=false`. Preserve existing working identities,
mounts, roots and durable evidence. Do not deploy unrelated local Roads commits
as part of this gate exercise. No production enablement, restart, user-project
repair or permission change was performed. Independent review:
[cycle review](rollout-cycle-independent-review.md).
