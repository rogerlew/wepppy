# Initial discovery seeds

Scaffold evidence, 2026-09-17 UTC. This is not a complete audit or a defect list.
Line numbers are deliberately omitted; enumerate symbols and callers during M1.

| Area / source | Observed mechanism | Required investigation |
| --- | --- | --- |
| `wepppy/nodb/mods/postfire_debris_flow/production.py`, `signature`, `cached_digest`, `get_state` | Size, mtime, ctime; optional hash; digest cache keys | Reproduce hard-link false staleness; separate cache invalidation from accepted-result equality |
| `wepppy/microservices/rq_engine/postfire_debris_flow_routes.py` | File signature comparison | Keep route/worker/report definitions compatible |
| `wepppy/nodb/mods/postfire_debris_flow/report.py`, `open_attachment` | Before/after file metadata guard | Preserve detection of concurrent changes; metadata recheck is not necessarily a defect |
| Post-fire `soil_inputs.py`, `soil_snapshot.py` | Device/inode/size/mtime/ctime and SQLite state | Preserve coherent main/WAL snapshots and publication guards |
| `wepppy/runtime_paths/wepp_inputs.py`, `copy_input_file`; `wepppy/nodb/core/wepp.py`, `_prep_channel_climate` | Hard-link materialization | Confirm source metadata effects and archive-backed path behavior; do not replace working links merely to hide consumer defects |
| `wepppy/nodb/_derived_build.py`, `file_signature`, `_identity` | Path/device/inode, mtime and size | Trace Climate/RAP callers and equal-size/restored-mtime rewrites |
| `wepppy/nodb/mods/features_export/dependency_tracker.py` | Existence, size, mtime, optional SHA-256 | Inspect actual equality and content-hash modes, propagation to export readiness |
| `wepppy/nodb/base.py` | NoDb cache and write-conflict metadata | Classify cache optimization versus persistence safety before any change |
| `wepppy/nodb/config_builder/registry.py` | Stat-keyed registry cache | Determine whether metadata only causes safe recomputation |
| `wepppy/nodb/core/landuse.py`; `wepppy/nodb/mods/baer/sbs_map.py` | Path/mtime/size fingerprints | Trace cached content and real invalidation boundaries |
| Geneva geometry/HSG collaborators; Omni contrast builder | Source/output mtime ordering | Establish whether completion-order or content dependency semantics are intended |
| `wepppy/wepp/reports/hillslope_watbal.py` | Source/cache mtime ordering | Equal-size preserved-time replacement and cache correctness |
| `wepppy/weppcloud/utils/assets.py`; `wepppy/webservices/dtale/dtale.py` | mtime/size cache identity | Browser/build/data cache stale-content risks |
| `wepppy/runtime_paths/fs.py`; browse/query-engine metadata | File versions/listing metadata | Separate display, transport caching, extraction and dependency decisions |
| RQ/preflight, RedisPrep and completion-event consumers | Completion timestamps/state | Trace downstream invalidation; do not infer file content from job completion alone |

## Execution discovery protocol

Start with `rg -n 'st_ctime|ctime_ns|st_mtime|mtime_ns|ModTime|LastWriteTime'`
and `rg -n 'file_signature|fingerprint|content_hash|sha256|digest|ETag|etag'`
over tracked source, configuration and operational scripts. Search JavaScript
`mtimeMs`/`ctimeMs`, shell `stat`/`test -nt`, and language-specific equivalents.
Inventory writers (`os.link`, copy/move/replace, chmod/chown, archive extraction,
SQLite backup/checkpoint) and consumers together. Follow wrappers and call sites.
Include tests as corroboration; generated/vendor files may be excluded only with
recorded provenance to their maintained source. Retain exact commands/revision.

For each entry record symbol/callers, producer, persisted schema, claimed identity,
content versus provenance rules, stat/hash caching, race boundaries, actual user
impact, representative file sizes/filesystem, tests, owner contract, disposition
and evidence. Also inspect genuine content-hash mechanisms for stale hash-cache
keys; searching ctime alone would miss false-current cases.
