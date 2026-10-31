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
restore retains root inode; the repair fences before destruction and retires
copied catalog identities after extraction.

| Writer/reader | Ordering/fields/observable consequence | Disposition and evidence |
| --- | --- | --- |
| `nodb/redis_prep.py` dump | HGETALL before open(w); excludes locked only; complete hash snapshot can regress/truncate | Repaired; real process ordered-capture, reader, kill and stage-failure tests pass |
| RedisPrep init/lazy_load | Missing file sets loaded/dumps; per-field restoration can expose saved true marker early | Repaired; fresh/empty/legacy, two-loader and WATCH live-writer conflict tests pass |
| RedisPrep setters | attrs, timestamps, rq, archive; mutation before dump; repeated HDEL for all timestamps | Repaired; grouped update/delete and committed-live/file-failure tests pass |
| `rq/project_rq_fork.py` rewrite | Temp/fsync/replace; strips rq, archive, Omni completion; mode 0600 | Shared coordinated atomic writer; fork preservation, root/snapshot symlink and 0600 tests pass |
| `rq/project_rq.py` reset | Whole hash delete then per-field population after copied rewrite | Atomic explicit reset preserves unrelated fields; real receipt-removal/reload tests pass |
| `project_rq.py` inherited receipts | Direct HDEL per receipt then dump | Grouped mutation/persistence; removed receipts remain absent on reload |
| `routes/weppcloudr.py` cleanup | Direct HDEL then dump inside best-effort caller boundary | Actual cleanup consumer and reload test pass; existing best-effort logging retained |
| Postfire preflight notify | Own Redis lease, atomic pipeline timestamp/model/policy/revision then dump | Shared grouped update protocol; postfire suite and live-writer conflict tests pass |
| Postfire production notify | Direct revision HSET without dump | Participates in coordination with persist=False; existing live-only behavior retained |
| `nodb/base.py` mirrors | locked:* and last_modified share some hashes; lock authority is separate keys | Cold recovery/explicit reset tests preserve unrelated live fields; WATCH catches concurrent writes |
| Go preflight2 HGETALL | Reads timestamps/locks/last_modified without loaded gating | Atomic Redis transaction removes partial visibility; real HGETALL reader coverage; Go HTTP checklist not exercised |
| WEPP route/context readers | Direct HGET/HGETALL timestamp reads | Real atomic restore and retained RQ receipt consumer tests pass; no all-route runtime claim |
| Omni contrast snapshot | Reads JSON timestamps; decode failure becomes None, changes eligibility | Actual Omni JSON reader succeeds after copied snapshot reset |
| Postfire report | Snapshot existence/non-symlink gates optional currentness | Postfire report regression suite and real service-identity snapshot access pass |
| Submission recovery / WEPP / RHEM | Reads rq receipts and checks real RQ state | Real RQ job retained during metadata deletion/recovery; duplicate admission blocked; missing job stays missing |
| Archive/restore | Catalog/config/Roads guards; archive includes dump; extraction writes member in place | Real archive roundtrip, incoming mode, extraction failure/kill, root fence and nested collision tests pass |
| Project delete/recreate and latest copy | Destructive replacement, sometimes same root path | Old-wrapper recreation fence, latest/batch initialization guards and two real leaf-boundary tests pass |
| Skeletonize | Retains dump; allowlist omits profile namespace file | Only traced caller is culvert flow; profile invocation unproven, namespace omission remains explicit open boundary |

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

## State and failure coverage assessment

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

## Final disposition — 2026-10-31 UTC

52 snapshot tests pass with disposable real Redis and NFS files. 183 direct
consumer tests pass, including archive nested catalog retirement. The matrix
records bounded evidence, not universal namespace isolation. Physical bind-mount
aliases, multi-host locks and profile skeletonization are unproven. Existing
basename collisions remain outside authorized schema migration. Historical
partial-loaded state requires operator reconciliation, explicitly accepted.
See validation.md for exact commands, revision provenance and retained logs.
