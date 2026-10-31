# RPS-01 bounded consumer and state inventory

Source inspection at `967627f4c`, 2026-10-31 UTC. This is not runtime parity proof.
Search: RedisPrep imports/callers, direct `redisprep.dump` paths, direct hash
operations, NoDb lock/mirror producers, submission and project lifecycle helpers,
Go preflight/status and retained fork tests. Extend when implementation exposes
another shared assumption. Dispositions below distinguish confirmed source defects
from untested integration; no row is verified unaffected solely by inspection.

## Identity and lifetime

DB 0 live metadata uses basename(wd), except `.redisprep-run-id` validates
`profile;;fork;;leaf`. File is `<wd>/redisprep.dump`; profile marker is separate.
NoDbBase uses different composite group/pup keys. Ordinary, batch/pup and Omni
scenario repeated leaf names can therefore alias RedisPrep hashes; unresolved
until representative configured paths prove isolation. No namespace migration
is authorized. Fork destinations are copies, not source generations. Archive
restore retains root inode and changes catalog incarnation after extraction.

| Writer/reader | Ordering/fields/observable consequence | Disposition and evidence |
| --- | --- | --- |
| `nodb/redis_prep.py` dump | HGETALL before open(w); excludes locked only; complete hash snapshot can regress/truncate | Confirmed defect by source; deterministic runtime characterization pending |
| RedisPrep init/lazy_load | Missing file sets loaded/dumps; per-field restoration can expose saved true marker early | Confirmed defect by source; fresh/empty/legacy and two-loader/live-writer tests pending |
| RedisPrep setters | attrs, timestamps, rq, archive; mutation before dump; repeated HDEL for all timestamps | Confirmed publication exposure; multi-field reset and crash-gap evidence pending |
| `rq/project_rq_fork.py` rewrite | Temp/fsync/replace; strips rq, archive, Omni completion; mode 0600 | Atomic byte path exists, coordination/access parity unresolved; existing fork tests cover preservation/symlink |
| `rq/project_rq.py` reset | Whole hash delete then per-field population after copied rewrite | Confirmed coherent-reset defect; preserve intentional fork reset while retaining unrelated live ownership |
| `project_rq.py` inherited receipts | Direct HDEL per receipt then dump | Confirmed shared publication exposure; test removed receipts survive reload |
| `routes/weppcloudr.py` cleanup | Direct HDEL then dump inside best-effort caller boundary | Confirmed shared publication exposure; preserve logged best-effort semantics |
| Postfire preflight notify | Own Redis lease, atomic pipeline timestamp/model/policy/revision then dump | Shared publication exposure; pipeline atomicity exists, restore interaction unresolved |
| Postfire production notify | Direct revision HSET without dump | Live revision not guaranteed durable; do not invent a persistence guarantee |
| `nodb/base.py` mirrors | locked:* and last_modified share some hashes; lock authority is separate keys | Unrelated live fields; ordinary whole-hash deletion prohibited; concurrent mirror test pending |
| Go preflight2 HGETALL | Reads timestamps/locks/last_modified without loaded gating | Confirmed partial-restore exposure; actual checklist consumer test pending |
| WEPP route/context readers | Direct HGET/HGETALL timestamp reads | Shared partial visibility exposure; representative coherent-read test pending |
| Omni contrast snapshot | Reads JSON timestamps; decode failure becomes None, changes eligibility | Confirmed corrupt-publication consumer; actual normal reader test pending |
| Postfire report | Snapshot existence/non-symlink gates optional currentness | Unresolved regression/access check |
| Submission recovery / WEPP / RHEM | Reads rq receipts and checks real RQ state | Shared receipt-loss consequence; metadata-loss test must retain RQ jobs |
| Archive/restore | Catalog/config/Roads guards; archive includes dump; extraction writes member in place | Confirmed lifecycle boundary requiring common coordination; real archive/readback pending |
| Project delete/recreate and latest copy | Destructive replacement, sometimes same root path | Unresolved participation/old-wrapper fence; test old operation across replacement |
| Skeletonize | Retains dump; allowlist omits profile namespace file | Unresolved supported profile invocation; retain namespace if supported |

All `wepppy/` paths above are relative to repository root with that prefix unless
explicitly identified as Go services. Concrete anchors: `redis_prep.py:201,212`,
`project_rq.py:2745,2769`, `project_rq_fork.py:1212`,
`project_rq_archive.py:291,400,433-473`,
`services/preflight2/internal/server/server.go:378`,
`omni_state_contrast_mixin.py:962`, `postfire_debris_flow/preflight.py:17`.

## Field authority

Persist attrs/timestamps/rq/archive and compatible other scalar metadata;
`last_modified` is independently written. Exclude `locked:*` both directions.
Submission leases, postfire lease and authoritative NoDb lock tokens are separate
keys, not snapshot records. No further exclusion is presumed without a traced
field and explicit contract amendment. A saved job ID does not imply job existence.

## State and failure coverage to execute

- Absent file/hash, empty object, live hash without file, missing/false loaded
  marker, loaded legacy hash, known interrupted legacy restore, corrupt/non-object/
  unreadable snapshot; distinguish live deletion from speculative recovery.
- Ordinary/profile/batch/pup/scenario paths, physical aliases, fork copied reset,
  archived/restored/skeletonized state, missing directory and same-path recreation.
- Serialization, exclusive temp creation, write/short-write, file fsync, replace,
  postcommit directory fsync/cleanup/release failures; preserve last good bytes.
- Paused older capture, newer capture, two processes, direct deletion and multiple
  loaders vs live mutation; final artifact plus actual restored consumer semantics.
- Coordination unsupported/lost/busy, owner death, release/replacement-owner safety,
  lifecycle lock ordering and runtime access/modes; no lease-check-only fencing.

Actual mount observation: workspace `/home` ext4; `/wc1` NFSv4.2, `local_lock=none`,
soft mount. Existing catalog source explains POSIX record-lock interoperability.
Neither observation proves new-protocol cross-host/identity parity.
