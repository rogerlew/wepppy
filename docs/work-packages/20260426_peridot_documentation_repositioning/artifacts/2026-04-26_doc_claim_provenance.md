# Peridot Documentation Claim Provenance (2026-04-26)

This artifact records evidence labels used during the Peridot documentation repositioning package.

## Label Definitions

- `confirmed`: directly evidenced by source code, tests, generated artifacts, or command output.
- `inference`: reasoned from source structure or observed behavior, but not independently benchmarked.
- `hypothesis`: plausible or historically asserted, but requiring dedicated benchmark or validation evidence before reuse as a measured result.

## Provenance Table

| Claim | Label | Evidence | Documentation location | Notes |
| --- | --- | --- | --- | --- |
| Peridot should be framed as an explicit graph abstraction rather than a simple TOPAZ/TOP2WEPP modernization. | `inference` | Shared `FlowpathCollection` model, channel network parsing, WBT/TOPAZ input support, explicit schema/manifest outputs. User guidance required this framing. | `/home/workdir/peridot/README.md`, `docs/benchmarks.md`, `docs/migration/prepwepp-to-peridot.md` | Architecture supports the framing; formal graph-theory proof/publication is out of scope. |
| Current watershed CLIs write Parquet tables and generated manifests directly. | `confirmed` | `/home/workdir/peridot/src/watershed_abstraction/watershed_abstraction.rs`, `/home/workdir/peridot/src/wbt/wbt_watershed_abstraction.rs`, `/home/workdir/peridot/src/watershed_abstraction/watershed_manifest.rs`, `/home/workdir/peridot/tests/watershed_parquet_manifest.rs`. | `/home/workdir/peridot/docs/contracts/watershed-output-contract.md` | Old README CSV language was corrected as a docs/runtime mismatch. |
| Current watershed CLI paths do not write `watershed/channels.csv`, `watershed/hillslopes.csv`, or `watershed/flowpaths.csv`. | `confirmed` | Source audit found Parquet writer calls in current CLI paths; CSV writer helpers exist in `flowpath_collection.rs` but are not called by the watershed abstraction functions. | `/home/workdir/peridot/docs/contracts/watershed-output-contract.md`, `/home/workdir/peridot/docs/migration/prepwepp-to-peridot.md` | WEPPpy historical compatibility/migration code may still handle CSV-only older runs. |
| `--skip-flowpaths` omits `flowpaths.parquet` and flowpath `.slps` outputs. | `confirmed` | `write_flowpaths` guards in `/home/workdir/peridot/src/watershed_abstraction/watershed_abstraction.rs` and `/home/workdir/peridot/src/wbt/wbt_watershed_abstraction.rs`. | `/home/workdir/peridot/docs/contracts/watershed-output-contract.md`, `/home/workdir/peridot/docs/operations.md` | The `slope_files/flowpaths/` directory may still be created. |
| WBT `--representative-flowpath` forces full flowpath export off. | `confirmed` | `/home/workdir/peridot/src/bin/wbt_abstract_watershed.rs` computes `skip_flowpaths=true` when representative mode is enabled; WBT abstraction also sets `write_flowpaths=false`. | `/home/workdir/peridot/README.md`, `/home/workdir/peridot/docs/contracts/watershed-output-contract.md`, `/home/workdir/peridot/docs/operations.md` | Documented as an intentional abstraction mode. |
| Representative-flowpath mode can reduce output volume by omitting per-pixel flowpath outputs. | `confirmed` for output omission; `hypothesis` for workload-specific wall-time speedups. | Output guards confirm omission. No new benchmark was run in this package. | `/home/workdir/peridot/docs/benchmarks.md`, WEPPpy procurement and culvert docs. | Numeric speedup claims now require dataset/hardware/version evidence. |
| Peridot supports topology flexibility/correctness metrics across TOPAZ, WBT, representative-flowpath, and sub-field modes. | `inference` | Multiple CLI modes and explicit schema/provenance fields exist; tests cover representative selection and manifest schemas. | `/home/workdir/peridot/docs/benchmarks.md` | Dedicated topology benchmark suite is follow-up work. |
| Watershed CLI process exit status is not sufficient success evidence for all write-stage failures. | `confirmed` | `/home/workdir/peridot/src/bin/abstract_watershed.rs` and `/home/workdir/peridot/src/bin/wbt_abstract_watershed.rs` discard underlying abstraction `Result` with `let _ = ...` then return `Ok(())`. | `/home/workdir/peridot/docs/contracts/watershed-output-contract.md`, `/home/workdir/peridot/docs/operations.md` | Follow-up runtime hardening recommended. |
| `field_flowpaths.csv` has duplicate `topaz_id` header names. | `confirmed` | `/home/workdir/peridot/src/watershed_abstraction/flowpath_collection.rs::write_field_subflows_metadata_to_csv` writes two `topaz_id` header labels. | `/home/workdir/peridot/docs/contracts/watershed-output-contract.md`, `/home/workdir/peridot/docs/migration/prepwepp-to-peridot.md` | Follow-up schema cleanup recommended; not changed under docs-only scope. |
| Historical Peridot speedup statements such as `3x to 10x` or `10x to 100x` apply universally. | `hypothesis` | Existing WEPPpy prose contained narrative claims, but this package did not find/run benchmark artifacts sufficient to generalize them. | `/home/workdir/peridot/docs/benchmarks.md`, `/workdir/wepppy/docs/projects/i-crews/st_joe/procurement-request.md`, `/workdir/wepppy/docs/culvert-at-risk-integration/dev-package/README.md` | WEPPpy docs now avoid presenting these as universal measured claims. |

## Follow-Up Recommendations

- Runtime hardening package: make `abstract_watershed` and `wbt_abstract_watershed` return non-zero for every propagated abstraction error.
- Schema cleanup package: rename or disambiguate duplicate `topaz_id` headers in `field_flowpaths.csv` with compatibility notes.
- Benchmark package: generate dataset-specific Peridot benchmark artifacts for full-flowpath, skip-flowpaths, representative-flowpath, and sub-field modes.
