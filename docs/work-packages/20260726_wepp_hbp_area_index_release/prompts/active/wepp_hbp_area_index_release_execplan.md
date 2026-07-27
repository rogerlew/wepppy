# Repair direct-HBP hillslope area indexing and publish the corrected release

This ExecPlan is a living document maintained according to
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, a direct-HBP watershed run will associate each hillslope with
its own positive area. The incident run will complete native interchange and
Omni hillslope summaries without a final-row `NAType` failure.

## Progress

- [x] (2026-07-27 UTC) Reproduced the shifted area sequence and final zero.
- [x] (2026-07-27 UTC) Located the Fortran lower-bound mismatch.
- [x] (2026-07-27 UTC) Implemented explicit one-based metadata slices.
- [x] (2026-07-27 UTC) Built and executed the generated incident replay.
- [x] (2026-07-27 UTC) Validated WEPPpyo3 and WEPPpy consumers.
- [x] (2026-07-27 UTC) Published and vendored the corrected release.
- [x] (2026-07-27 UTC) Completed dual review and disposition.
- [ ] Complete WEPPpy commit/push and Forest regeneration.

## Surprises & Discoveries

- Observation: HBP bytes were correct; `H587.hbp` encodes about 801.42 square
  metres while `loss_pw0.txt` reported zero.
  Evidence: the LOSS area sequence for rows 1, 2, and 586 matched HBP shards
  2, 3, and 587 respectively.
- Observation: WEPPpyo3 required no schema or parser change.
  Evidence: its released Python 3.12 extension converted the regenerated LOSS
  and SOIL files with zero rejected records.

## Decision Log

- Decision: Pass `hlarea(1:nhill)` and `dia(:,1:nhill)` to the reader.
  Rationale: The legacy common arrays begin at zero while the reader dummy
  arrays and hillslope identifiers are one-based.
  Date/Author: 2026-07-27 UTC / Codex.
- Decision: Cut a new release rather than overwrite `wepp_260726`.
  Rationale: Historical binary names and hashes are immutable provenance.
  Date/Author: 2026-07-27 UTC / Codex.
- Decision: Rerun only watershed aggregation for the base and three Omni
  scenarios.
  Rationale: Existing HBP shards contain correct area metadata; the repaired
  code is exercised when the watershed binary reads those shards.
  Date/Author: 2026-07-27 UTC / Codex.

## Outcomes & Retrospective

Pending completion.

## Context and Orientation

`fpm-src/hillslope_binary_pass_reader.f90` parses each HBP shard.
`src/hbp_mode2_bridge.f90` transfers its metadata into WEPP common arrays.
Those legacy arrays include element zero, but watershed hillslopes occupy
indices 1 through `nhill`. `src/endchn.for` writes those areas to
`loss_pw0.txt`. WEPPpyo3 converts that text to parquet, and WEPPpy
`HillSummaryReport` uses the area to normalize runoff and sediment.

## Plan of Work

Repair the bridge association, add regression coverage, build sequentially,
and replay the copied incident watershed using its existing verified HBP
shards. Assert each annual and average LOSS hillslope area is positive and
matches the corresponding HBP metadata at output precision. Cut a new WEPP
release with notes and hashes. Convert generated LOSS and SOIL through
WEPPpyo3, then vendor both binaries and sidecars into WEPPpy. Exercise native
interchange and Omni report tests. Obtain independent code and QA reviews,
disposition findings, commit and push all repositories, and finally rerun the
targeted Forest workload.

## Concrete Steps

Run the WEPP build with `make clean && make all_gfortran` from
`/workdir/wepp-forest_260430_baseline/src`. Execute the copied incident
`pw0.run` from its `wepp/runs` directory using the candidate watershed binary.
Run focused and full WEPP tests plus binary smoke and provenance gates. Run
WEPPpyo3 Rust and Python release tests and direct conversions. Install the
release into `wepp_runner/bin`, validate hashes and loaders, then run focused
WEPPpy interchange, reports, Omni, and runner tests with `wctl`.

For Forest regeneration, first require:

    hostname
    sha256sum /workdir/wepppy/wepp_runner/bin/wepp_260727 \
      /workdir/wepppy/wepp_runner/bin/wepp_260727_hill

The required hashes are `cbcfac30e484613c5314e7a91b694863d26138905fcf04947650bc2c6c148918`
and `d79a4bfde31feab8e3aff5ea5ae5d14b898f85b5f8fae5e471bc43d4078eddcc`.
Then use the run-scoped `Wepp` facade to persist `wepp_260727`, run hillslopes
with `max_workers=4`, and run watershed aggregation:

    wepp = Wepp.getInstance("/wc1/runs/md/mdobre-foursquare-fovea")
    wepp.wepp_bin = "wepp_260727"
    wepp.run_hillslopes(max_workers=4)
    wepp.run_watershed()

This regenerates matching-version HBP shards before the watershed reader is
called and uses bounded concurrency for the slow NAS.

## Validation and Acceptance

Acceptance requires generated evidence, not only static tests. The copied and
Forest `loss_pw0.txt` files must each contain 587 unique average hillslope rows
with minimum area greater than zero; row 587 must be `0.080 ha`. WEPPpyo3 must
produce the expected LOSS columns and 587-row average hillslope parquet.
`HillSummaryReport` and Omni compilation must complete.

## Idempotence and Recovery

All source builds and copied-run replays are repeatable. Preserve
`wepp_260726`; use a new release name. Before the Forest rerun, verify host and
run paths and use only the run-scoped orchestration entry point. No service
restart is authorized.

## Artifacts and Notes

Validation and review evidence will be recorded under this package's
`artifacts/` directory.

## Interfaces and Dependencies

The HBP binary schema and WEPPpyo3 parquet schemas remain unchanged. The only
source interface correction is the one-based actual slice passed to
`hbp_reader_get_metadata`.
