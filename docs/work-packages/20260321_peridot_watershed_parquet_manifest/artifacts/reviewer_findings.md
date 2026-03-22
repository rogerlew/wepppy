# Reviewer Findings (`reviewer`)

## Initial pass (2026-03-21)

### Medium: README manifest drift after WEPPpy post-processing
- Evidence: Peridot generated `watershed/README.md` before WEPPpy added `wepp_id`/`chn_enum` to parquet outputs.
- Risk: README file manifest/schema could become stale relative to canonical parquet files.

### Medium: Flowpaths parquet write executed in parallel with other heavy writers
- Evidence: `write_subflows_metadata_to_parquet` was all-in-memory and previously scheduled inside parallel output task pool.
- Risk: avoidable peak-memory and IO contention on large flowpath-enabled runs.

## Fixes implemented
- Added README refresh in WEPPpy post-processing to update file manifest/schema sections after parquet normalization:
  - `wepppy/topo/peridot/peridot_runner.py` (`_refresh_watershed_readme`, `_build_manifest_*` helpers, call in `post_abstract_watershed`).
- Moved Peridot flowpaths parquet write out of the parallel task pool:
  - `peridot/src/watershed_abstraction/watershed_abstraction.rs`
  - `peridot/src/wbt/wbt_watershed_abstraction.rs`

## Re-review result (2026-03-21)
- README drift issue: **Resolved**.
- Parallel-memory contention issue: **Downgraded to Low residual risk** because flowpaths parquet writer still materializes full columns in memory before write (`flowpath_collection.rs`).

## Residual risks
- Low: very large flowpath exports can still hit high memory usage due to single-batch parquet materialization. Candidate follow-up: chunked/row-group streaming writer.
