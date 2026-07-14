# Build and validate a reusable sub-field channel-connectivity inventory

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must stay current as
work proceeds. Maintain it according to
`docs/prompt_templates/codex_exec_plans.md`.

This is a secondary, bounded plan that may run concurrently with
`docs/work-packages/20260713_ag_fields_concept2_watershed_integration/prompts/completed/ag_fields_concept2_watershed_integration_execplan.md`.
It does not replace or block that primary plan.

## Purpose / Big Picture

After this work, a maintainer can point a Peridot command at compatible aligned
AgFields rasters and receive a deterministic JSON answer to a narrow question: how
many distinct sub-fields have one or more generated per-cell flowpaths whose first
cell outside the sub-field is a mapped channel. The command is demonstrated on
`/wc1/runs/sa/sacral-self-discipline` without changing that project.

The inventory describes mapped topology. It does not estimate water or sediment
delivery and does not validate buffer effects.

## Progress

- [x] (2026-07-13 20:59 UTC) Opened the separate non-blocking work package and
  inventoried the dev-project Parquet schemas.
- [x] (2026-07-13 20:59 UTC) Located Peridot's existing D8 trace and channel-cell
  semantics.
- [x] (2026-07-13 21:09 UTC) Implemented reusable library logic and a CLI with
  explicit raster paths, deterministic JSON, optional channel-mask/output paths,
  and contextual grid errors.
- [x] (2026-07-13 21:09 UTC) Added six focused tests and Peridot command
  documentation.
- [x] (2026-07-13 21:09 UTC) Passed formatting, focused/full tests, and debug
  compilation without rebuilding or staging preexisting release binaries.
- [x] (2026-07-13 21:09 UTC) Ran both channel-detection modes on the designated
  project, recorded the invocation/result, and
  verified its inputs remained unchanged.
- [x] (2026-07-13 21:09 UTC) Committed and pushed Peridot commit `8343b8f`.
- [x] (2026-07-13 21:09 UTC) Prepared the completed WEPPpy package record and this
  plan for archival and intentional publication.

## Surprises & Discoveries

- Observation: The dev project contains 6,626 `fields.parquet` rows and 126,416
  `field_flowpaths.parquet` rows.
  Evidence: PyArrow schema and row-count inspection on 2026-07-13.
- Observation: Peridot already defines a channel hit as a positive explicit channel
  mask cell, or as a `subwta` TOPAZ identifier ending in `4` when no mask is
  supplied.
  Evidence: `/workdir/peridot/src/roads_trace/trace_downslope.rs` function
  `is_channel_cell`.
- Observation: The Parquet tables are not required for this existence metric.
  `sub_fields_abstraction` starts a path at every retained sub-field cell and stops
  after appending its first cell outside the sub-field.
  Evidence: `/workdir/peridot/src/watershed_abstraction/watershed_abstraction.rs`
  functions `walk_flowpaths` and `walk_flowpath`.
- Observation: Default TOPAZ suffix-4 channel detection and an explicit
  `netful.tif` positive-cell mask return the same four dev-project metrics.
  Evidence: Two live CLI runs completed on 2026-07-13.

## Decision Log

- Decision: Use explicit resource arguments instead of accepting a WEPPcloud run
  root.
  Rationale: This keeps Peridot reusable and makes every data dependency visible in
  the reproducible invocation.
  Date/Author: 2026-07-13 / Roger Lew and Codex.
- Decision: Limit v1 output to direct sub-field and outlet-cell counts.
  Rationale: The user requested simple metrics, and Mariana will evaluate the
  science; adding delivery or buffer heuristics would exceed this package.
  Date/Author: 2026-07-13 / Roger Lew and Codex.
- Decision: Preserve the Concept 2 plan as the primary active plan.
  Rationale: This inventory is explicitly non-blocking and can execute in parallel.
  Date/Author: 2026-07-13 / Roger Lew and Codex.
- Decision: Test the generated path boundary directly instead of reconstructing
  full traces from Parquet centroids.
  Rationale: One generated path begins at every retained cell and ends after its
  first outside cell. A D8 successor outside the current sub-field that is also a
  channel is therefore exact evidence for the requested existence count.
  Date/Author: 2026-07-13 / Codex.
- Decision: Reject dimensions, affine geotransforms, or projections that do not
  align.
  Rationale: Elementwise comparison of shifted but same-shaped rasters could return
  plausible, incorrect counts.
  Date/Author: 2026-07-13 / Codex.

## Outcomes & Retrospective

Peridot commit `8343b8f` implements the library and CLI without a new dependency.
All 46 debug test cases pass. The live inventory reports 3,269 of 6,626 retained
sub-fields with direct channel drainage, 3,357 without, and 12,365 direct channel
outlet cells. The explicit `netful.tif` result matches the default SUBWTA rule.
The three required input hashes remained unchanged. The result is intentionally a
path-boundary topology count, not buffer or mass-delivery evidence.

## Context and Orientation

The Peridot repository is `/workdir/peridot`. Its `sub_fields_abstraction` command
produces `sub_field_id_map.tif`, in which every positive identifier is one retained
agricultural sub-field within a parent WEPP hillslope. It also starts one D8 path at
every positive raster cell. D8 means each cell routes to one of its eight neighbors
according to the flow-vector raster. The generated path follows cells with the same
sub-field identifier, appends the first outside cell, and stops.

The final command names three required aligned rasters: the retained sub-field ID
map, `subwta.tif`, and the raw WhiteboxTools `flovec.tif`. SUBWTA identifies channel
cells by TOPAZ identifiers whose final digit is `4`. A caller may instead pass an
aligned integer channel mask whose positive cells are channels. The flowpath
Parquet metadata is useful for a cross-check but is not a required input.

Peridot's existing Whitebox-to-TOPAZ remapper and `PATHS` D8 offsets own the
direction mapping. The CLI reuses them and must not know the `/wc1/runs` directory
convention. It reads its three or four input rasters and writes JSON only to
standard output or an explicit `--out-json` path.

The Peridot working tree contains preexisting modified release binaries at
`target/release/abstract_watershed` and
`target/release/wbt_abstract_watershed`. They belong to the user. Do not overwrite,
stage, revert, or commit them, and do not run a release build.

## Plan of Work

The implemented library function
`peridot::subfield_channel_connectivity::summarize_subfield_channel_connectivity`
validates every raster against the sub-field map's dimensions, affine geotransform,
and projection. It scans positive sub-field cells, remaps each valid D8 direction to
its successor, requires the successor to be outside the current sub-field, and then
tests it against the explicit mask or SUBWTA convention. Hash sets ensure each
qualifying sub-field is counted once while outlet cells remain a direct count.

The named binary in `Cargo.toml` and
`src/bin/subfield_channel_connectivity.rs` requires `--sub-field-map`, `--subwta`,
and `--wbt-flovec`; accepts `--channel-mask` and `--out-json`; remaps raw WBT D8
codes; and emits pretty schema-versioned JSON. Raster read/alignment errors return a
nonzero exit through Rust's normal error path.

Six synthetic tests cover one-time sub-field aggregation, multiple outlet cells,
an explicit mask, the first-outside-cell invariant, dimension mismatch, affine
shift, and projection mismatch. Peridot's README documents resource meanings and
the scientific limitation.

Validation ran only in debug mode. Both channel-detection variants were invoked
with explicit paths for `sacral-self-discipline`, and their identical JSON metrics
are captured in the tracker. SHA-256 checks before and after prove the three
required run inputs did not change. Only intentional source/docs were staged;
preexisting dirty release binaries were preserved.

## Concrete Steps

Work in `/workdir/peridot` for implementation:

    git status --short --branch
    cargo fmt --all -- --check
    cargo test subfield_channel_connectivity
    cargo check --bin subfield_channel_connectivity
    cargo test
    cargo run --quiet --bin subfield_channel_connectivity -- \
      --sub-field-map /wc1/runs/sa/sacral-self-discipline/ag_fields/sub_fields/sub_field_id_map.tif \
      --subwta /wc1/runs/sa/sacral-self-discipline/dem/wbt/subwta.tif \
      --wbt-flovec /wc1/runs/sa/sacral-self-discipline/dem/wbt/flovec.tif
    cargo run --quiet --bin subfield_channel_connectivity -- \
      --sub-field-map /wc1/runs/sa/sacral-self-discipline/ag_fields/sub_fields/sub_field_id_map.tif \
      --subwta /wc1/runs/sa/sacral-self-discipline/dem/wbt/subwta.tif \
      --wbt-flovec /wc1/runs/sa/sacral-self-discipline/dem/wbt/flovec.tif \
      --channel-mask /wc1/runs/sa/sacral-self-discipline/dem/wbt/netful.tif

Work in `/home/workdir/wepppy` for package validation:

    wctl doc-lint --path docs/work-packages/20260713_ag_fields_flowpath_channel_connectivity/package.md
    wctl doc-lint --path docs/work-packages/20260713_ag_fields_flowpath_channel_connectivity/tracker.md
    wctl doc-lint --path docs/work-packages/20260713_ag_fields_flowpath_channel_connectivity/prompts/completed/ag_fields_flowpath_channel_connectivity_execplan.md
    wctl doc-lint --path PROJECT_TRACKER.md

Preview US-spelling normalization with `uk2us` and require an empty diff for every
changed Markdown file.

## Validation and Acceptance

Acceptance is satisfied. Focused tests prove that a sub-field is counted once when
multiple outlet cells enter a channel, that an interior positive mask cell does not
qualify, and that unaligned grids fail. Formatting, debug compilation, and all 46
tests passed without changing release artifacts.

Both real-data commands exited zero and printed valid JSON. The identities
`3269 + 3357 = 6626` and `3269 <= 6626` reconcile, and both channel definitions
report 12,365 direct channel outlet cells. The tracker contains the exact command,
metrics, and hashes.

## Idempotence and Recovery

All reads and tests are repeatable. Without `--out-json`, the CLI writes only to
standard output, so a failed or interrupted run can be retried without cleanup. If
input validation fails, correct the explicit path/grid and rerun; never patch the
dev project in place. If a debug command changes the two preexisting release
binaries, stop and coordinate with their owner instead of discarding user changes.

## Artifacts and Notes

Cross-check evidence:

    fields.parquet rows: 6,626
    field_flowpaths.parquet rows: 126,416
    distinct retained subfields in raster and Parquet: 6,626

Generated-data result:

    subfields_total: 6626
    subfields_with_direct_channel_drainage: 3269
    subfields_without_direct_channel_drainage: 3357
    direct_channel_outlet_cells: 12365

Peridot commit: `8343b8f` (`Add subfield channel connectivity CLI`).

## Interfaces and Dependencies

The implementation uses the existing Peridot crate, Clap, Serde JSON, raster type,
WBT D8 remapper, and `watershed_abstraction::PATHS`; it adds no dependency.
`SubfieldChannelConnectivitySummary` exposes total, with/without direct drainage,
and outlet-cell counts. `SubfieldChannelConnectivityError` exposes shape,
geotransform, and projection mismatches. All paths remain caller supplied.

Revision note (2026-07-13 20:59 UTC): Initial plan created to capture the user's
resource-oriented CLI decision and allow implementation to proceed independently
of Concept 2.

Revision note (2026-07-13 21:09 UTC): Replaced the initial Parquet-centroid trace
sketch with the as-built path-boundary raster contract and recorded tests,
generated-data metrics, immutable-input evidence, and Peridot commit.
