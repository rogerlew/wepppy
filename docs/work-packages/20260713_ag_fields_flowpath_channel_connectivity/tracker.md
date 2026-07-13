# Tracker - AgFields Flowpath-to-Channel Connectivity Inventory

> Living record for the reusable Peridot inventory and its first generated-data
> result.

## Quick Status

**Timezone**: UTC

**Started**: 2026-07-13 20:59 UTC

**Current phase**: Closed

**Last updated**: 2026-07-13 21:09 UTC

**Next milestone**: None; Mariana may use the inventory during scientific
evaluation without blocking Concept 2

**Security impact**: `none`

**Dedicated security review**: `no`

**Security artifact**: N/A

## Task Board

### Ready / Backlog

None.

### In Progress

None.

### Blocked

None. This package is explicitly non-blocking for Concept 2.

### Done

- [x] Defined the separate package boundary, simple metric goal, and immutable dev
  project (2026-07-13 20:59 UTC).
- [x] Confirmed `fields.parquet` contains 6,626 sub-fields and
  `field_flowpaths.parquet` contains 126,416 representative flowpaths in the dev
  project (2026-07-13 20:59 UTC).
- [x] Implemented explicit raster inputs, deterministic JSON, optional channel-mask
  and output paths, and full grid-alignment validation in Peridot (2026-07-13
  21:09 UTC).
- [x] Added six focused unit tests and passed the full Peridot suite (2026-07-13
  21:09 UTC).
- [x] Reproduced the same dev-project metrics with the SUBWTA suffix rule and the
  explicit `netful.tif` channel mask (2026-07-13 21:09 UTC).
- [x] Pushed Peridot commit `8343b8f` to `origin/main` (2026-07-13 21:09 UTC).

## Timeline

- **2026-07-13 20:59 UTC** - Package opened as a non-blocking companion to Concept
  2 and Peridot CLI implementation began.
- **2026-07-13 21:09 UTC** - Peridot implementation, full tests, real-project
  inventory, independent channel-mask check, and push completed; package closed.

## Decisions Log

### 2026-07-13 20:59 UTC: Build a reusable resource-oriented CLI

**Context**: A one-off notebook or run-specific script could produce the initial
count but would hide resource assumptions and be difficult to repeat.

**Decision**: Put the implementation in Peridot and require explicit input paths.
The CLI must not infer `/wc1/runs` or write into the project.

**Impact**: The same topology inventory can be repeated on any compatible resource
set and incorporated into later evaluation workflows.

### 2026-07-13 20:59 UTC: Keep the first metric intentionally narrow

**Context**: The immediate question is how many sub-fields have at least one
flowpath that reaches a channel. Buffer fidelity and delivery effects require
science evaluation.

**Decision**: Report direct counts only. Do not add delivery ratios, buffer
heuristics, sediment/water weighting, or scientific pass/fail labels.

**Impact**: The output is auditable topology evidence, not a claim about Concept 2
scientific fidelity.

### 2026-07-13 20:59 UTC: Run concurrently without gating Concept 2

**Context**: The user requested that the investigation proceed independently while
Concept 2 remains the selected delivery track.

**Decision**: Keep the Concept 2 ExecPlan as the primary active plan. This package
has its own bounded ExecPlan and no dependency edge that blocks Concept 2.

**Impact**: A failure or scientific ambiguity in this inventory does not pause the
weighted PASS implementation.

### 2026-07-13 21:09 UTC: Use the generated path boundary instead of retracing Parquet centroids

**Context**: Discovery confirmed that `sub_fields_abstraction` starts one flowpath
at every retained sub-field raster cell and appends the first cell outside the
sub-field before stopping. The Parquet table summarizes those paths but does not
need to be replayed to answer an existence question.

**Decision**: A sub-field has direct channel drainage when at least one retained
cell's D8 successor is outside that sub-field and is a channel. Use the retained
sub-field ID raster, SUBWTA, and raw WhiteboxTools FLOVEC as the required inputs;
allow a positive-cell channel mask to override the SUBWTA suffix-4 convention.

**Impact**: The command is linear in raster cells, avoids centroid reconstruction,
and exactly matches the boundary where generated sub-field paths stop. It does not
claim routing through intervening buffers or non-field hillslope areas.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Direct drainage is mistaken for buffer or mass-routing fidelity | Medium | Medium | Name the metric precisely and document exclusions | Mitigated |
| Raster grids are same-sized but shifted or use different projections | Medium | Low | Validate dimensions, affine geotransform, and projection | Closed |
| Explicit channel mask marks an interior sub-field cell | Medium | Low | Require the tested channel cell to be the first cell outside the current sub-field | Closed |
| Generated-data run mutates the dev project | Medium | Low | Read inputs and emit stdout JSON; verify SHA-256 hashes before/after | Closed |

## Verification Checklist

### Peridot

- [x] `cargo fmt --all -- --check` passes.
- [x] Six focused tests for connectivity and grid validation pass.
- [x] `cargo check --bin subfield_channel_connectivity` passes without a release
  build.
- [x] Full `cargo test` passes: 46 tests across library, binary, integration, and
  doc-test targets; two preexisting unused-import warnings remain.

### Generated Data

- [x] Every required resource is named explicitly in the recorded command.
- [x] The CLI completes against `sacral-self-discipline` and emits valid JSON.
- [x] The primary sub-field count and minimal supporting totals are recorded.
- [x] SUBWTA suffix-4 and explicit `netful.tif` channel detection agree exactly.
- [x] The three required dev-project input hashes are unchanged after execution.

### Documentation

- [x] Peridot documents the command and metric meaning.
- [x] WEPPpy package, tracker, ExecPlan, and root project tracker are current.
- [x] Markdown lint and US-spelling preview pass.
- [x] Parameterization ADR remains correctly classified as not applicable.

## Progress Notes

### 2026-07-13 20:59 UTC: Package opening and input discovery

**Agent/Contributor**: Codex

**Work completed**:

- Separated the connectivity inventory from Concept 2 delivery.
- Located the dev project's sub-field and flowpath Parquet resources.
- Confirmed Peridot already owns raster and downstream D8/channel-trace logic.
- Began the Peridot CLI and tests concurrently with package documentation.

**Next steps**:

- Review the implemented metric contract and validation behavior.
- Run focused debug tests and the real-project invocation.
- Record results, commit both repositories intentionally, and push.

**Test results**: Initial work-package Markdown lint and spelling preview passed.

### 2026-07-13 21:09 UTC: Implementation, generated-data validation, and closeout

**Agent/Contributor**: Codex

**Work completed**:

- Added the `peridot::subfield_channel_connectivity` report/error contract and the
  `subfield_channel_connectivity` Clap binary.
- Added explicit required `--sub-field-map`, `--subwta`, and `--wbt-flovec` paths,
  optional `--channel-mask` and `--out-json`, WBT D8 remapping, and schema-versioned
  deterministic JSON.
- Added dimension, affine-geotransform, projection, explicit-mask, aggregation, and
  first-outside-cell regression coverage.
- Ran the default and explicit-mask variants on the dev project and pushed Peridot
  commit `8343b8f`.

**Exact default invocation**:

    cd /workdir/peridot
    cargo run --quiet --bin subfield_channel_connectivity -- \
      --sub-field-map /wc1/runs/sa/sacral-self-discipline/ag_fields/sub_fields/sub_field_id_map.tif \
      --subwta /wc1/runs/sa/sacral-self-discipline/dem/wbt/subwta.tif \
      --wbt-flovec /wc1/runs/sa/sacral-self-discipline/dem/wbt/flovec.tif

**Observed metrics**:

    subfields_total: 6626
    subfields_with_direct_channel_drainage: 3269
    subfields_without_direct_channel_drainage: 3357
    direct_channel_outlet_cells: 12365

Adding
`--channel-mask /wc1/runs/sa/sacral-self-discipline/dem/wbt/netful.tif`
produced the same four values.

**Input SHA-256 before and after**:

    e183d707d02ee1d4c84e4372d5d1883f8df9dc6bf2b01093e322b26dd0887b77  sub_field_id_map.tif
    43554eb57f941c85019be303e576218993d50b194094224b1e55ccad336e0d43  subwta.tif
    f13af3a40ee91a114fd22115b36a972dbe9f43b1af516f7335bb5e4f1172911c  flovec.tif

**Test results**: Formatting, focused tests, binary check, full `cargo test`, live
default/mask runs, `git diff --check`, and Peridot README spelling preview passed.
Full tests reported 46 passes and two unrelated preexisting unused-import warnings.

**Next steps**: None for engineering. Mariana may use the inventory as topology
evidence while retaining the documented scientific limitation.

## Watch List

- The output must retain a clear distinction between “a generated flowpath's first
  outside cell is a mapped channel” and “modeled water/sediment delivery reaches a
  channel.”
- Any later metric that follows routing beyond the first cell outside a sub-field
  is a different contract and needs separate naming and evaluation.

## Communication Log

### 2026-07-13 20:59 UTC: Parallel non-blocking investigation

**Participants**: Roger Lew, Codex

**Outcome**: Build the reusable Peridot CLI now, run it on
`sacral-self-discipline`, and keep it independent of Concept 2 engineering
delivery. Mariana owns later science evaluation.
