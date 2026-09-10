# Forest rollback baseline

2026-09-09 UTC. Host forest; WEPPpy master at 00ddde799 before execution,
wepppyo3 main at 2c31f6c. Contract checkpoints: WEPPpy 94c57af2a and
febd8f2d3; wepppyo3 072aed8.

Complete 5.6 GiB run copy (including controller state, soils, inputs, outputs,
reports and local orchestration files):
`/tmp/kslast-area-weighted-20260909/run-baseline`.
Old raster native library and wrapper together:
`/tmp/kslast-area-weighted-20260909/native/raster_characteristics`.
Copies used cp -a --reflink=auto; no files deleted or archives flattened.

Local run `/wc1/runs/se/seductive-sabra`, 505 hillslopes, 46 simulation years,
MOFE enabled, configured model wepp_260430, scalar kslast 0.05. Source map
`/geodata/extended_mods_data/wepppy-locations-portland/bedrock/combined_ksat_map.tif`:
SHA256 da8f26c8ccc12871b5b282a13c3096a2c1203f5dd0085ae5547e434979f64c33.
Grid `dem/topaz/SUBWTA.ARC`:
SHA256 ec503509a164e45f6cf780784caacf07028e3aca04ccfaedd3c01adef0bfe8e1.
Default, batch and fork-archive queues had zero queued and started jobs.

Recovery: drain local work, preserve failed outputs separately, stop local
Compose, restore the backed-up run tree preserving permissions, restore the
matching library/wrapper via sibling staging and rename, then start Compose.
Use canonical clear_nodb_file_cache for affected controllers before resubmission;
do not replay old RQ jobs or flush Redis globally. Keep both snapshots until
acceptance and operator retention disposition.

Discovery: NoDir thaw/materialization is retired. Directory-only runtime is
current authority; archive-only fails and mixed roots use their directory.
The contract was amended before implementation. NaN warp staging avoids finite
sentinel collisions; saved conductivity nodata is -9999.
