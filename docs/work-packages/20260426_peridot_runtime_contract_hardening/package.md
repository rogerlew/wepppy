# Peridot Runtime Contract Hardening

**Status**: Closed (2026-04-26)
**Timezone**: UTC

## Overview

This package turned two documented Peridot follow-ups into an executable runtime hardening effort. The first closed a CLI error-contract gap where `abstract_watershed` and `wbt_abstract_watershed` could discard propagated `io::Result` failures and still return success. The second cleaned up the ambiguous duplicate `topaz_id` header in `sub_fields_abstraction` `field_flowpaths.csv` output while preserving the parent-hillslope `topaz_id` contract expected by WEPPpy.

The package is tracked in WEPPpy because WEPPpy owns orchestration, post-processing, and work-package governance, while primary implementation edits landed in `/home/workdir/peridot` with companion WEPPpy compatibility/docs updates.

## Objectives

- Make `abstract_watershed` return a non-zero process exit whenever the underlying abstraction returns an error.
- Make `wbt_abstract_watershed` return a non-zero process exit whenever the underlying abstraction returns an error.
- Disambiguate `field_flowpaths.csv` headers so there is no duplicate `topaz_id` column.
- Preserve the parent hillslope/subcatchment column name `topaz_id` for compatibility, and name the flowpath record's own topaz column `flowpath_topaz_id`.
- Update WEPPpy `post_abstract_sub_fields` to normalize both new outputs and historical CSVs where pandas may have mangled the duplicate header to `topaz_id.1`.
- Update Peridot contract/migration/operations docs and WEPPpy AgFields/data-table docs so downstream consumers see the new schema clearly.
- Add regression tests that would have failed against the pre-package behavior and pass after the hardening changes.

## Scope

### Included

- Peridot CLI changes in:
  - `/home/workdir/peridot/src/bin/abstract_watershed.rs`
  - `/home/workdir/peridot/src/bin/wbt_abstract_watershed.rs`
- Peridot CSV writer schema change in:
  - `/home/workdir/peridot/src/watershed_abstraction/flowpath_collection.rs`
- Peridot regression tests for CLI error propagation and field-flowpath CSV header uniqueness.
- WEPPpy compatibility normalization and tests for sub-field flowpath CSV-to-Parquet post-processing in:
  - `/workdir/wepppy/wepppy/topo/peridot/peridot_runner.py`
  - targeted WEPPpy tests under `/workdir/wepppy/tests/`.
- Peridot documentation updates for output contract, migration, and operations docs.
- WEPPpy documentation updates where AgFields/sub-field parquet schema is described.
- Validation artifacts recording command outputs and compatibility evidence.

### Explicitly Out of Scope

- Changing watershed output table schemas unrelated to `field_flowpaths.csv`.
- Changing the scientific representative-flowpath or sub-field abstraction algorithms.
- Rebuilding or committing Peridot release binaries unless explicitly requested as a deployment step.
- Changing WEPPpy RQ queue wiring, route contracts, auth, or NoDb state contracts.
- Retrofitting historical run artifacts in `/wc1/runs`; this package updates forward behavior and reader compatibility only.

## Stakeholders

- **Primary**: WEPPpy and Peridot maintainers responsible for watershed abstraction and AgFields outputs.
- **Reviewers**: Peridot runtime maintainers, WEPPpy topology/AgFields maintainers, data-table/query consumers.
- **Security Reviewer**: Not required unless implementation expands into subprocess invocation, queue wiring, route surfaces, or path/input trust boundaries beyond the scoped CLI return-code behavior.
- **Informed**: Operators who deploy Peridot binaries into WEPPpy, documentation maintainers, AgFields users.

## Success Criteria

- [x] `abstract_watershed` no longer discards the underlying abstraction `Result`; propagated errors make the process exit non-zero.
- [x] `wbt_abstract_watershed` no longer discards the underlying abstraction `Result`; propagated errors make the process exit non-zero.
- [x] Regression coverage proves the CLI error contract through injected abstraction error paths in both CLI wrappers.
- [x] `field_flowpaths.csv` headers are unique and include `flowpath_topaz_id` for the flowpath record column while retaining parent `topaz_id`.
- [x] WEPPpy `post_abstract_sub_fields` accepts both new `flowpath_topaz_id` and historical pandas-mangled `topaz_id.1` inputs and emits canonical Parquet with `flowpath_topaz_id`.
- [x] Peridot docs are updated to remove the known duplicate-header gap and document the canonical field-flowpaths schema.
- [x] WEPPpy docs are updated where they describe AgFields sub-field table outputs.
- [x] Peridot targeted tests pass.
- [x] WEPPpy targeted tests pass.
- [x] WEPPpy work-package docs pass `wctl doc-lint`.

## Compatibility and Regression Plan

This package changes a run-scoped CSV/Parquet schema contract, so compatibility must be explicit before implementation.

- Keep `topaz_id` as the parent hillslope/subcatchment ID column in `field_flowpaths.csv`.
- Rename only the duplicate flowpath-record topaz column to `flowpath_topaz_id`.
- In WEPPpy post-processing, normalize historical CSVs by mapping pandas' likely duplicate-header name `topaz_id.1` to `flowpath_topaz_id` when the canonical column is absent.
- If both `flowpath_topaz_id` and `topaz_id.1` are present, fail explicitly rather than guessing.
- Cast `topaz_id`, `flowpath_topaz_id`, `sub_field_id`, and `fp_id` to nullable Int32 where applicable before writing Parquet.
- Add tests for new Peridot CSV headers and WEPPpy normalization of both new and historical CSV forms.
- Do not mutate historical run artifacts during package execution; compatibility is reader/post-processing behavior only.

## Dependencies

### Prerequisites

- Peridot documentation repositioning package completed and pushed:
  - `/workdir/wepppy/docs/work-packages/20260426_peridot_documentation_repositioning/`
  - `/home/workdir/peridot/docs/contracts/watershed-output-contract.md`
- Existing Peridot source and tests in `/home/workdir/peridot`.
- Existing WEPPpy sub-field post-processing in `/workdir/wepppy/wepppy/topo/peridot/peridot_runner.py`.

### Blocks

- Operator confidence that Peridot watershed CLI success/failure status can be trusted by orchestration.
- Downstream consumers that need unambiguous AgFields flowpath table schemas.
- Future generated documentation or schema catalog work for Peridot sub-field outputs.

## Related Packages

- **Depends on**: [20260426_peridot_documentation_repositioning](../20260426_peridot_documentation_repositioning/package.md).
- **Related**: [20260321_peridot_watershed_parquet_manifest](../20260321_peridot_watershed_parquet_manifest/package.md).
- **Related**: [20260422_peridot_side_hillslope_length_capping](../20260422_peridot_side_hillslope_length_capping/package.md).
- **Related**: [20260327_roads_peridot_trace_core](../20260327_roads_peridot_trace_core/package.md).

## Timeline Estimate

- **Expected duration**: 1-2 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Medium, because one change affects process failure semantics and one affects a run-output schema.

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: Scope is reliability and schema-contract hardening for existing local binaries and post-processing. It does not add auth, public routes, uploads/downloads, secrets, queue wiring, shell command construction, or new external egress.
- **Security review artifact**: `N/A`

## Hardening and Callus Softening

- **Failure signature(s)**:
  - `abstract_watershed` or `wbt_abstract_watershed` can return process success even if the underlying abstraction returns an `io::Error` from a write-stage path.
  - `field_flowpaths.csv` has duplicate `topaz_id` headers, which causes ambiguous CSV access and pandas-style mangling such as `topaz_id.1`.
- **Related prior hardening efforts**:
  - [Peridot Documentation Repositioning](../20260426_peridot_documentation_repositioning/package.md) documented both gaps as follow-ups.
- **Health signals**:
  - Peridot CLI failure status matches missing/unwritable output failures.
  - Generated `field_flowpaths.csv` has unique headers.
  - WEPPpy post-processing accepts both current and historical field-flowpath CSV forms.
- **Danger signals**:
  - Tests rely only on source-text assertions instead of observable failure behavior.
  - A user-visible column is renamed without compatibility normalization.
  - Runtime changes expand beyond the two scoped defects.
- **Observation window**: First deployment cycle after updated binaries and WEPPpy post-processing are promoted.
- **Temporary calluses introduced**: None planned.
- **Callus softening hypothesis**: Not applicable; this package removes ambiguity rather than adding a temporary mitigation.

## References

- `/home/workdir/peridot/src/bin/abstract_watershed.rs` - CLI wrapper now propagates `abstract_watershed(...)` results.
- `/home/workdir/peridot/src/bin/wbt_abstract_watershed.rs` - CLI wrapper now propagates `wbt_abstract_watershed(...)` results.
- `/home/workdir/peridot/src/watershed_abstraction/flowpath_collection.rs` - `write_field_subflows_metadata_to_csv` now writes `flowpath_topaz_id` for the flowpath-record topaz column.
- `/home/workdir/peridot/docs/contracts/watershed-output-contract.md` - canonical Peridot output contract to update.
- `/workdir/wepppy/wepppy/topo/peridot/peridot_runner.py` - WEPPpy sub-field post-processing from CSV to Parquet.
- `/workdir/wepppy/wepppy/nodb/mods/ag_fields/README.md` - AgFields output documentation.
- `/workdir/wepppy/docs/dev-notes/data_tables_standardization.spec.md` - data table ID standardization notes.
- `/workdir/wepppy/docs/work-packages/20260426_peridot_documentation_repositioning/artifacts/2026-04-26_doc_claim_provenance.md` - provenance for the two follow-up defects.

## Deliverables

- Peridot runtime patch for CLI error propagation.
- Peridot CSV schema patch for unique `field_flowpaths.csv` headers.
- WEPPpy compatibility normalization patch for historical and new field-flowpath CSVs.
- Peridot and WEPPpy regression tests.
- Updated Peridot and WEPPpy docs.
- Validation artifact under this package.

## Follow-up Work

- Rebuild and deploy Peridot binaries into WEPPpy after code merge if the implementation package does not include deployment artifacts.
- Optional historical-run migration tooling if operators later decide existing `field_flowpaths.parquet` files should be rewritten; not required for forward compatibility.

## Closure Notes

**Closed**: 2026-04-26

**Summary**: Completed cross-repo runtime/schema hardening. Peridot watershed CLI entrypoints now propagate abstraction `io::Result<()>` errors, and `field_flowpaths.csv` now uses unique `flowpath_topaz_id` headers while preserving parent `topaz_id`. WEPPpy normalizes new and historical sub-field flowpath CSV schemas before writing canonical Parquet.

**Lessons Learned**: The duplicate-header cleanup needed a compatibility rule before implementation because pandas' historical `topaz_id.1` behavior had effectively become an implicit reader contract. Injected CLI wrapper tests were the smallest reliable way to cover propagated errors without relying on filesystem-permission behavior that may differ under root/container execution.

**Post-close validation addendum**: Peridot commit `e09f54c` (`Fix Peridot full-suite regressions`) closed the support interpolation and raster fixture/GDAL failures observed during initial closeout. Local `cargo test` now passes across library, CLI-wrapper, integration, and doctest suites. The remaining local Peridot loose end is preexisting dirty `target/release/*` binaries, which stay out of source commits unless deployment scope is explicitly requested.

**Archive Status**: Complete; active ExecPlan archived under `prompts/completed/`.
