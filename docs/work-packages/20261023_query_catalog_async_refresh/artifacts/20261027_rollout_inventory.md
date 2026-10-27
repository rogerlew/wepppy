# Production catalog inventory and capacity gate

**Disposition: HOLD.** Read-only measurements ran on wepp1 from
2026-10-26 23:50:58 UTC through 2026-10-27 00:04 UTC. The actual inventory helper
was exercised as the existing batch worker identity **1002:130**, without scope
creation, receipts, refresh, admission, Redis mutation or production config edits.
[Structured evidence](20261027_rollout_inventory.json) contains aggregate counts,
source/trace hashes, identity observations and exact limits. Raw candidate names
and resumable cursors remain in protected task scratch only.

## Traversal results

The installed `query_catalog_rq.py` matches the workspace SHA256
`b8b8e9a9cae212333d694e2e1f56df5fdd313a611f09bd5aea0d35f07d0bfa5c`.
The probe called its unmodified `_inventory_step` with 100 nodes per tick;
symlink exclusion and project detection semantics were preserved.

| Root | Measured outcome | Completion |
| --- | --- | --- |
| `/wc1/runs` | 46 ticks, 4,600 directory nodes, 2,735 unique candidate scopes: 2,192 top-level and 543 nested | Incomplete; 125 pending nodes including 121 shard nodes |
| `/wc1/batch` | Root accessible; full traversal not reached | Unmeasured |
| `/wc1/culverts` | Root accessible; full traversal not reached | Unmeasured |
| `/geodata/weppcloud_runs` | First actual 100-node tick did not return after at least 137 seconds | Incomplete; no completed tick/cursor publication |

Completed primary ticks consumed **705.681 seconds** of enumeration. Tick
minimum/median/p95/maximum: **4.067 / 15.049 / 30.076 / 42.883 seconds**. Three
exceeded the 30-second cadence; none exceeded the 60-second lease. There were no
reported errors in completed primary ticks. Counts exclude the following
interrupted tick and are lower bounds, not a complete fleet inventory.

An initial progress interpretation mistakenly treated absence of ten-tick stdout
updates as a slow first tick; the persisted per-tick log disproved that inference.
The figures above use measured ticks only. The separate legacy failure is real:
its first call never produced a completed tick. Python's 120-second diagnostic
alarm could not report promptly while blocked in an NFS call; process state was
`D`, wait channel `rpc_wait_bit_killable`. Only that owned diagnostic was terminated.

## Legacy namespace is required

A read-only PostgreSQL transaction found **12,931** catalog rows with legacy
locations, including **5,403 owned** rows. Across all legacy rows, 33 had access
and 27 modification timestamps within 90 days. Catalog location records are not
a substitute for a full filesystem inventory.

Ten most recently active owned legacy filesystem witnesses were checked directly:
all ten exist with project markers, all ten were accessed within 90 days, five
were modified within 90 days, none is a symlink, and none has a corresponding
`/wc1/runs/<shard>/<runid>` directory. They are not aliases of the primary root.
All ten were readable/executable and writable under service-identity `os.access`
checks; six have catalogs. No write was attempted. Raw identifiers remain private.

Excluding legacy from the proposed root configuration would omit real owned
projects and is not a valid way to make the gate pass. The smallest namespace
set covers four physical roots: runs/sharded, batch/batch, culverts/culverts and
legacy/flat. Preserve canonical namespaces `wc1:runs`, `wc1:batch`, `wc1:culverts`
and `legacy:runs`; configure legacy coordination through
`/wc1/query-engine-coordination/locks`. Known alternate path aliases must not be
silently reinterpreted as standalone scopes.

Within each host, `/wc1` and `/geodata/wc1` aliases identify the same corresponding
inodes. wepp1/wepp2 batch workers can write the legacy root and coordination
parent. On wepp3, the fork/archive worker sees `/geodata` aliases and legacy root
read-only, while `/wc1/query-engine-coordination/locks` is writable. This is an
existing role/mount distinction, not authorization to change mounts or permissions.
Cross-host inode values differ and are not used as identity proof; existing
shared-guard evidence is separate. Access predicates alone do not prove publication.

## Bounded listing diagnosis

No production implementation was edited for these probes.

| Method | Result |
| --- | --- |
| Full `os.listdir`, no child metadata | Timed out after 65 seconds; traceback stayed in `os.listdir` |
| First 100 `os.scandir` entries | 0.000342 seconds after 0.007895-second open; warm first page only |
| Same 100 entries, `is_dir(follow_symlinks=False)` | 0.000045 seconds, 38 directories |
| Same entries, existing `Path.is_dir` plus symlink test | 0.107086 seconds, identical 38-directory filter |
| Full `os.scandir` with nofollow directory filter | Timed out after 60 seconds; last progress 10,000 entries / 3,308 directories at 33.535 seconds |

The full streaming probe's 30-second traceback was at iterator advancement, not
entry classification. Its initial 5,000 entries were warm and fast, but the
whole listing was not. Replacing eager child metadata checks may help; neither
that change nor `scandir` alone is proven to fit the lease. The directory-node
limit does not bound work required to enumerate one very large directory.
Do not promote a first-page timing into complete-cycle acceptance.

## Capacity interpretation

At uninterrupted 30-second cadence, 100 nodes and 25 admissions per tick imply
arithmetic ceilings of 288,000 nodes and 72,000 admissions per day. Those are not
observed service capacity. Even the **2,735 observed primary scopes alone** require
at least 110 admission slots, or **3,300 seconds** of nominal cadence, if each
requires admission. Full counts, complete-cycle duration, oldest unreconciled age,
actual maintenance queue delay and sustained refresh service capacity remain
unestablished by this probe. The legacy tick exceeds the inventory lease before
any admission work, independently blocking rollout acceptance.

## Cleanup and retained evidence

The parent requested a bounded primary stop. After the next observed completed
tick (45 to 46), only probe PID 1963 was terminated at **00:02:49 UTC**; its last
complete cursor remains resumable. Owned legacy PID 2410 was separately terminated.
Both exited 143. The bounded name-only and full-streaming probes exited 124 at
their external deadlines; the first-page comparison exited successfully. Final
process inspection shows only existing docker-init/RQ workers, with no owned
inventory/listing diagnostic left running. No service restart occurred.

Private scratch: `/wc1/query-catalog-validation/20261026/inventory-20261026T235058Z`
and `inventory-20261026T235625Z-legacy`. Primary candidate-list, cursor and tick
hashes, harness/log hashes and cleanup record are in the JSON evidence. No private
project-path list is committed.

Independent correctness/security disposition: **HOLD is supported**. The probes
preserved production state and identities; aggregate evidence demonstrates both
necessary legacy coverage and an unresolved complete-cycle/lease boundary. A
one-scope canary or spare-worker snapshot cannot close this fleet gate. This
review authorizes no deployment, runtime reconfiguration or silent root exclusion.
