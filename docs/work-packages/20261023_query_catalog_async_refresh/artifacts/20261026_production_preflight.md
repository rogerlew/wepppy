# Production preflight — 2026-10-26

**Disposition: retain disabled rollout.** Fleet compatibility and a narrowly scoped production-identity publication probe passed. Shared-lock handoff latency and production reconciliation capacity remain open acceptance gates. No deployment, global configuration, queue admission or real-project mutation was performed.

Authority: [refresh contract](../../../schemas/query-engine-catalog-refresh-contract.md), [ADR-0104](../../../adrs/ADR-0104-query-catalog-refresh-operational-bounds.md), and [operations guide](../../../dev-notes/query-catalog-refresh-operations.md). Parent authorized production read-only inspection, followed by isolated scratch guard/publication testing under existing identities and mounts. Structured observations, timestamps, hashes and probe-source hashes are retained in [20261026_production_preflight.json](20261026_production_preflight.json).

## Fleet and effective configuration

Read-only observations began **2026-10-26 17:16 UTC**. Verified host checkout heads: wepp1/wepp2 `813d912be1c8f6f13b6fc60cecebbef9259cd36e`; wepp3 `e5e59e83256a19ba5fc9b5f5c8401f3848e11e73`.

| Host | Eligible batch consumers | Other inspected participants | Shared storage |
| --- | --- | --- | --- |
| wepp1 | Four, all idle in both snapshots | Six default workers; web, rq-engine, query-engine, scheduler | NFS4.2 hard, NAS address 192.168.100.102 |
| wepp2 | Four, three idle and one busy | Six default workers | NFS4.2 hard, NAS address 192.168.100.101 |
| wepp3 | None | One fork-archive worker, idle | NFS3 soft, NAS address 192.168.100.101 |

The Redis worker registry contained **21 live workers**, all attributable to these five worker containers. No additional off-host/companion batch consumer appeared. This is a point-in-time inventory, not a guarantee about workers started later. The separate culvert application was not modified or treated as part of this Redis queue fleet.

All nine inspected service containers run as **uid 1002 / gid 130**, supplementary group 130, with PID1 umask **0022**. Every live worker advertises refresh **protocol 1**, `enabled=false`, and the same disabled-mode default root mapping. No `QUERY_CATALOG_*` environment variables were set in any inspected container. Enabled rollout still requires explicit roots; the disabled default mapping is not an approved rollout configuration.

Fresh Python interpreters inside all nine containers imported the same native scanner extension SHA256:

`7908a4fa667b149f4eee5a827dfb65c39c0c080369459b659c68cec26f411811`

The `catalog_scan` export exists. Deployed publication source SHA256 is `1f19401a875246e621fdeea398cf4f42d6fb288eef591ad5d611c19b6fd3dcd5`; queue source is `b8b8e9a9cae212333d694e2e1f56df5fdd313a611f09bd5aea0d35f07d0bfa5c`, identical across inspected containers. These are fresh-process imports and files, not an attachment to each long-lived worker's loaded address space. No production GIL benchmark or exhaustive native scan was performed.

## Root and permission readiness

`/wc1/runs`, `/wc1/batch`, `/wc1/culverts` and `/wc1/query-engine-coordination/locks` exist and are accessible for read/write/traversal to the actual service identity on all three hosts. Their owners are 1002:130; modes respectively 0775, 02775, 02775 and 02755. These checks establish access, not full project-tree permission coverage.

Use the canonical three-namespace configuration as the candidate: `wc1:runs`/sharded, `wc1:batch`/batch and `wc1:culverts`/culverts, under their `/wc1` paths with external coordination `/wc1/query-engine-coordination/locks`. Deployment ownership must confirm this selection before staging it consistently in producers, scheduler and all eligible consumers. Do not silently include legacy roots merely because disabled defaults list them. `/geodata/weppcloud_runs` exists, is not writable from wepp3, and its bounded listing was slow. A missing or excluded managed namespace must remain explicit; no fallback mapping is authorized.

## Production-identity scratch guard and publication

Only `/wc1/query-catalog-validation/20261026/async-preflight-1719` was created. Its process-local namespace is `qcat-rollout-preflight-20261026`; its `runs` and external `locks` directories are separate from real run trees. Scratch directories retain uid1002/gid130 and inherited setgid mode 02755; the stable guard inode is 0640. No lock inode was deleted. Scratch remains retained for diagnosis.

An initial six-second hold attempt exceeded a 30-second client timeout for wepp2. The first harness raised before retaining all independent results, so it cannot establish exclusion failure or exact holder exit. All owned commands were subsequently absent. That limitation prompted one authorized diagnostic repeat with independently retained per-host timestamps and a 90-second acquisition budget.

The repeat used the actual `catalog_lifecycle_guard` and existing mounts:

| Participant | Import time | Acquisition wait | Observed result |
| --- | --- | --- | --- |
| wepp1 holder | 0.052 s | 0.026 s | Held 8 s, released and exited 0 |
| wepp3 contender | 0.099 s | 30.732 s | Acquired after holder release; exited 0 |
| wepp2 contender | 0.266 s | 33.111 s | Acquired after wepp3 release; exited 0 |

**No overlapping ownership was observed.** However, acquisition occurred about **24–26 seconds after the initial holder released**. Startup does not explain that delay. This is a measured shared-guard handoff latency concern, not evidence of broken exclusion or a sustained lock hang. One direction/trial does not certify every production lock topology. No mount settings were changed.

Sequential canonical synchronous activation plus required-path freshness validation then passed on every host for a three-row Parquet scratch artifact. Catalog schema selected `value: int64`; file size 518 bytes matched actual input. Timings include activation and consumer validation, not just native scanning:

| Host | Time | Catalog owner | Catalog mode |
| --- | --- | --- | --- |
| wepp1 | 4.834 s | 1002:130 | 0644, new file under existing umask |
| wepp2 | 11.977 s | 1002:130 | Preserved deliberately seeded 0640 |
| wepp3 | 7.562 s | 1002:130 | Preserved 0640 |

Each host read back the published entry successfully. No shared-queue job or global enable flag was used. These tiny-scope timings cannot be extrapolated into production project throughput.

## Bounded capacity observations

At **17:16:01** and **17:17:46 UTC**, batch/default/fork-archive queue lengths were zero. One of eight batch consumers was busy in both snapshots. Empty queues are instantaneous spare capacity evidence, not measured catalog queue delay or sustainable maintenance capacity.

Read-only shallow enumeration consumed at most 101 entries per root, without descending into projects:

| Root | Observed entries | Listing time | Completeness |
| --- | --- | --- | --- |
| `/wc1/runs` | 101 | 0.006 s | Truncated; shard nodes, not project count |
| `/wc1/batch` | 8 | 1.069 s | Top level only |
| `/wc1/culverts` | 59 | 3.469 s | Top level only |
| `/geodata/weppcloud_runs` | 101 | 59.245 s | Truncated |

The timing ends before sampled-entry directory classification; it does not include every metadata lookup. No inventory cursor exists for the disabled configuration. Total scopes, nested-project count, complete-cycle duration, oldest unreconciled scope and maintenance queue delay remain **unmeasured**. ADR-0104's defaults imply ceilings of 288,000 directory nodes and 72,000 admissions per day at uninterrupted 30-second ticks; these are arithmetic limits, not attainable-throughput evidence.

## Recommendation and remaining gates

Keep async refresh disabled while the separately owned `wepp_261021` full workflow acceptance proceeds. Retain this scratch scope and lock inode. Before enabling:

1. Diagnose or explicitly accept the measured 24–26-second post-release guard delay through a bounded production-mount latency acceptance exercise; preserve current identities and mounts unless a separately authorized change is justified.
2. Confirm deployment-owned namespaces and stage one explicit configuration through the existing service env-file/deployment mechanism. Recheck all eligible consumers at cutover, including newly started companions.
3. Obtain representative project and nested-scope counts, a complete bounded reconciliation cycle, oldest unreconciled age, service time distribution and shared-worker queue-delay evidence. A read-only shallow sample and idle-worker snapshot cannot certify the 24-hour target.
4. Complete the real scientific pipeline/report/browser acceptance under the required identities and orchestration. This preflight adds production guard/publication evidence; it does not replace that workflow gate.

No tracker, ExecPlan, deployment configuration or unrelated culvert files were edited by this probe task.

## Follow-up: lock handoff latency diagnosis

Read-only code and host inspection plus one sequential timing decomposition on the existing scratch scope narrowed the finding. Application `catalog_lifecycle_guard` calls blocking `fcntl.lockf` directly: it has no Python polling interval, sleep or retry loop. Its other operations are path/metadata validation, a process-local RLock, mkdir/open and unlock/close. The measured cross-host wait therefore is not the scheduler's 30-second cadence or catalog retry setting.

Production kernels are `6.8.0-110-generic` on wepp1/wepp2 and `6.8.0-136-generic` on wepp3. All expose lockd `nlm_timeout=10` and `nlm_grace_period=0`; these values alone do not explain a 30-second blocked-lock handoff. Upstream Linux 6.8 has more directly relevant waits:

- NFSv3's [lockd client](https://github.com/torvalds/linux/blob/v6.8/fs/lockd/clntproc.c) waits up to `NLMCLNT_POLL_TIMEOUT = 30*HZ` while awaiting a blocked-lock grant before retrying.
- The [NFSv4 client](https://github.com/torvalds/linux/blob/v6.8/fs/nfs/nfs4proc.c) uses `NFS4_LOCK_MAXTIMEOUT = 30*HZ` for its callback-aware blocked-lock wait. Its simpler path exponentially increases polling from one second to the same 30-second maximum.

The observed 30.7/33.1-second acquisition times are **consistent with those kernel wait/retry paths**. This is an inference from timing and upstream code, not proof that a particular callback was lost or that the deployed Ubuntu kernels followed a specific branch. No packet capture, kernel lock trace or NAS server configuration was inspected. A bounded kernel-journal query for 17:15–17:30 UTC returned no matching NFS/lockd/RPC diagnostic lines on any host; silence is not proof of healthy callbacks. No grace-period, polling, mount or network settings were changed.

### Uncontended phase timing

Timing wrappers in a fresh, isolated Python process preserved function behavior and recorded two uncontended guard acquisitions, one canonical scratch publication and one freshness check per host. No real project or shared queue was touched. Values below are seconds:

| Host | First / second full guard | Publication | Catalog-build phase | Freshness check |
| --- | --- | --- | --- | --- |
| wepp1 | 0.134 / 0.025 | 4.271 | 3.986 | 0.049 |
| wepp2 | 0.365 / 0.033 | 16.106 | 13.598 | 0.801 |
| wepp3 | 0.270 / 0.005 | 5.855 | 5.237 | 0.170 |

Individual `lockf` calls across these measurements took **0.0006–0.0421 seconds**. Uncontended locking therefore does **not** explain the several-second tiny-scope publication times. `_build_catalog` dominates this fresh-process measurement; that phase includes lazy native import, enumeration and alias canonicalization, so these observations do not attribute its entire duration to storage or scanner runtime. Atomic metadata writes and fsync were also timed in structured evidence; all resulting catalogs remained **1002:130 / 0640**. All probe commands exited successfully.

The remaining targeted diagnostic, if needed for rollout acceptance, is tracing one bounded contended scratch acquisition at the NFS client/server callback boundary. That would distinguish expected polling from unavailable grant notifications without changing synchronization semantics. Existing evidence supports preserving exclusion and investigating latency; it does not justify replacing the shared guard or altering production mounts.
