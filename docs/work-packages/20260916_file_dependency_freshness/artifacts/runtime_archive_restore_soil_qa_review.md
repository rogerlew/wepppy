# Live archive restore: independent soil-currentness attribution

Disposition: **archive byte/mode preservation passes at the measured scope;
automatic M3 currentness after restore fails for the existing PF-R01 physical
soil-inventory limitation.** The failure is explained, retained and not counted
as a successful currentness check. **Normal explicit API/RQ M3 rerun recovery
now passes**, including current state, browser, report query and downloads, as
recorded below. No production or test changes, source SQLite connections/checkpoints,
or acceptance mutations were made by this review.

## Actual result and isolation

The live archive and restore API/RQ jobs finished. The actual ZIP's selected
file/directory modes match; `runtime_archive_inventory_before.json` and
`runtime_archive_inventory_after.json` preserve all545 selected climate,
post-fire and report artifacts plus84 directory modes. This inventory excludes
mutable root logs/controller bookkeeping and is not a universal all-file claim.

`runtime_restore_freshness_diagnosis.json` records the accepted attempt
`6e31becce1644fb782d341f2d3dd4156` with:

- source snapshot currentness **false**;
- strong accepted artifact currentness **true**;
- only `soil_inputs` different within source selections;
- ordinary source records changed timestamps, while their selected paths/sizes
  and content hashes match;
- replacing only `selections.soil_inputs` in a **deepcopy used solely for the
  comparison** makes `_source_snapshots_current` return true.

That control does not write state or authorize reuse. It isolates the exact
comparator responsible for the stale result; other unexplained content or
selection differences would still have made the comparison fail.

Independent [read-only byte evidence](runtime_restore_soil_attribution_qa.json)
and its [retained probe](runtime_restore_soil_attribution_qa.py) close the
remaining physical-byte question under the actual container UID1000/GID993:

1. All seven `sources_sha256` entries in the accepted soil manifest match the
   restored files, including prepared evidence, fallback raster, SSURGO raster
   and metadata.
2. Restored SQLite main, WAL and SHM bytes match their actual ZIP members.
3. Restored main and WAL bytes also match the accepted attempt's original
   `predictors/soil/snapshots/initial/cache.sqlite[-wal]` copies. SHM is compared
   with the archive only, since private snapshot reads may manage their own SHM.

All comparisons passed. Reads were ordinary bounded file/ZIP reads with file
generation checks; no SQLite engine was connected to a shared or copied source
for this attribution. The original accepted physical main/WAL bytes remain
available, so no speculative logical-equivalence claim is needed.

## Source trace and existing disposition

`production.py:sources(model='M3')` inserts
`production_soils.inventory(wd)` into `selections['soil_inputs']`.
`production_soils.py:inventory` returns:

- `dependencies`, from `soil_inputs.dependency_state`: path presence and raw
  device/inode/size/mtime/ctime tuples for soil/prepared inputs;
- `cache_state`, from `soil_snapshot.source_state`: corresponding main/WAL/SHM
  observations;
- prepared-source content hashes, which are unchanged here.

`production._source_snapshots_current` removes ordinary file timestamps from
content comparison but compares selections exactly. Archive extraction creates
new inode/time observations, so unchanged soil bytes still change those raw
selections. The control and independent byte comparisons reproduce this exact
mechanism, rather than infer it from the general fact that archives change
metadata.

The preexisting `postfire_remaining_freshness_review.md` explicitly describes
raw soil **dependency metadata as well as SQLite main/WAL/SHM**, and
`soil_logical_currentness_security_disposition.md` accepts justified deferral
without changing guards. This restore case falls within that same unfixed
PF-R01 class; it is broader operational evidence than the earlier SQLite-only
mutation examples, not a new archive corruption or silent false-current defect.

## Recovery and acceptance limit

The durable user/operator limitation is documented in
[`postfire_debris_flow/README.md`, Developer and Operator Notes](../../../../wepppy/nodb/mods/postfire_debris_flow/README.md#developer-and-operator-notes):
archive restore can leave intact saved artifacts with stale M3 status. Use the
normal explicit **Run M3** workflow to acquire current soil evidence and publish
a newly accepted result; then verify current/browser/download behavior. Do not
rewrite old provenance, force the comparison control into runtime state, rebuild
soils automatically, or weaken execution/publication guards.

Package archive acceptance must state both results: actual byte/mode restoration
passed, while preservation of automatic M3 currentness did not and remains a
disclosed PF-R01 limitation. Successful subsequent rerun establishes supported
recovery, not a retroactive pass for automatic post-restore currentness or a
PF-R01 correction.

## Verified normal recovery

`runtime_postfire_restore_recovery_jobinfo.json` records actual
`run_m3_rq` job `2d277b19-891a-4c3f-b410-0f9764393d49` finished without exception.
It publishes new attempt `7902bf9bc67840b180df10ee22329450`.
`runtime_postfire_restore_recovered_current.json` reports current freshness.

`runtime_browser_restore_recovered.json` shows current state before/after browser
reload, matching served/rendered controller IDs and zero page errors. The actual
saved report page also returns200/current with zero page errors
(`runtime_postfire_report_browser.json`); its attempt-scoped query returns200
with `summary.current=true` (`runtime_postfire_report_query_recovered.json`).
The initial query omitted required `attempt_id` and returned400; that failed
harness request remains retained and is not a successful query claim.

`runtime_reports_restore_recovered.json` records all five new M3 attachments,
C09 HTML/CSV and C08 HTML/cache Parquet returning200. The Parquet download SHA
matches the restored source file. C08 CSV remains the same existing500 adapter
defect, separately documented and never counted as passed.

This closes the live archive **preservation plus explicit recovery** workflow
at its stated scope. It does not promise that future restores preserve automatic
M3 currentness, change the soil logical-identity policy, or close the remaining
Omni live-RQ and interleaved-state package gates.
