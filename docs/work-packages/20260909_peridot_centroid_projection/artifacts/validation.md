# Validation evidence

Date: 2026-09-09 UTC. Peridot source: `3cef07b` (contract ancestor `98e8a43`, pre-task source `495abd5`). WEPPpy work-package checkpoint: `dd15f6191`. Final build SHA256/version strings are in [release_manifest.json](release_manifest.json).

## Automated checks

- `cargo test` from `/home/workdir/peridot`: 51 passed, including four new centroid tests and the existing Parquet/CSV/schema/CLI tests. Final log: `/tmp/peridot-centroid-final-tests.log`.
- `wctl run-pytest tests/topo --maxfail=1`: 158 passed, 4 skipped.
- `wctl run-pytest tests --maxfail=1`: 8146 passed, 72 skipped, 3110 warnings in 820.53 seconds. Log: `/tmp/wepppy-centroid-full-tests.log`.
- WEPPpy `wctl doc-lint` for package/ADR and Peridot `markdown-doc lint` for README, operations, and contract: passed, including final closeout lint.
- `git diff --check` in both scoped changesets: passed.

## Built binary execution

Build command: `cargo build --release --bin abstract_watershed --bin wbt_abstract_watershed --bin sub_fields_abstraction`. All three release outputs were copied into WEPPpy's canonical `wepppy/topo/peridot/bin/` directory and SHA256 equality verified. The two tracked Peridot release binaries are updated as well; the previously dirty copies are preserved in `/tmp/peridot-centroid-backup/preexisting-*`.

All three final vendored binaries executed successfully inside the existing WEPPcloud container through `wctl run-python`/`subprocess.run(check=True)`. Inputs were isolated under `/workdir/peridot/target/centroid-validation/container-*`. TOPAZ used seductive-sabra input raster copies with `--ncpu 4 --skip-flowpaths`; WBT used `tests/fixtures/wbt/amiss-polyhedron` with full flowpaths and `--ncpu 4`. Sub-fields used that WBT grid with a single synthetic field over its hillslopes. No live run was regenerated.

## Coordinate and output checks

[Container output results](container_output_validation.json), checked again from the final vendored build using [validate_container_outputs.py](validate_container_outputs.py): 505 TOPAZ hillslopes, 220 channels, 17 WBT hillslopes, 7 channels, 2291 flowpaths, 17 fields and 2291 field flowpaths agree with independent pyproj transformation of their stored pixel coordinates. Maximum observed discrepancy: 1.42e-14 degrees; acceptance tolerance: 1e-8 degrees.

[Source-baseline comparisons](generated_output_validation.json) use the unchanged source at 98e8a43, built from a temporary `git archive`, rather than assuming old vendored binaries represent current source. WBT and sub-field non-coordinate columns match exactly after row sorting; all 35 WBT and 34 sub-field slope artifacts match byte-for-byte. The source correction changes neither schemas nor pixel IDs.

TOPAZ caveat: 20 of 506 slope artifacts differ from the source-baseline run. A second run of the unchanged source-baseline binary also changes channel geometry and dependent hillslope dimensions/modes/areas. The same non-coordinate column set varies without this patch; TOPAZ byte parity is therefore not claimed. Its coordinates and schemas pass independently. This is a preexisting reproducibility issue, not a reason to silently change traversal algorithms in this package.

Prior binary drift: the old vendored sub-field flowpath CSV lacks the explicit `flowpath_topaz_id` column already in current Peridot source. Updating from current source brings that prior committed schema correction forward. No schema edit is part of this patch.

## Downstream soil propagation

[Soil results](soil_input_validation.json): regenerated coordinates sampled from the wepp1 bedrock raster reach real `prep_multi_ofe_hillslope` execution inside the WEPPcloud container. Hillslopes 202, 212, 232, 252, 263, 282, 292, and 293 write 0.0001 in all nine OFEs, replacing their previous 0.005. Inputs were copied to an isolated directory and source files were not modified. The [reproduction script](validate_soil_propagation.py) uses actual soil, management, and slope files, with one simulation year to bound validation cost.

## Timing observations

Single-run `/usr/bin/time -v` observations, not a throughput benchmark:

| Mode | Source baseline wall time | Corrected wall time | Baseline peak RSS | Corrected peak RSS |
| --- | --- | --- | --- | --- |
| TOPAZ, 505 hillslopes | 4.76 s | 4.70 s | 176832 KiB | 178660 KiB |
| WBT fixture | 0.17 s | 0.19 s | 67584 KiB | 71624 KiB |
| Sub-fields fixture | 0.19 s | 0.22 s | 64128 KiB | 67396 KiB |

No performance improvement is claimed. PROJ is initialized once per output writer and reused per row; no per-centroid initialization or new dependency was added.

## Reproduction and limitations

Host comparison script: [validate_generated_centroids.py](validate_generated_centroids.py), using `/tmp/peridot-centroid-validation/{topaz,wbt,fields}-{baseline,new}` and `topaz-baseline-repeat`. Each directory contains an isolated input copy and CLI output. Rust known-coordinate tests are committed in Peridot `tests/centroid_projection.rs` and do not require this production run.

`wctl doc-lint` cannot lint another repository by absolute path (markdown-doc panics when the file is outside its root); running `markdown-doc lint` from Peridot works. Runtime deployment to wepp1/wepp2 and live-run repair were not requested or performed. The Python raster sampler corner-rounding issue remains separate follow-up scope.
