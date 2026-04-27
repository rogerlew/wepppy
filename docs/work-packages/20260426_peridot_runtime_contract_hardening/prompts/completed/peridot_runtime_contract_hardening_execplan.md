# Peridot Runtime Contract Hardening ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this package is implemented, WEPPpy and operators can trust Peridot watershed CLI process status for propagated write-stage failures, and AgFields sub-field flowpath tables will have unambiguous column names. A user can see the hardening working by running targeted Peridot tests that prove CLI errors are not swallowed and by inspecting generated or test CSV headers showing `flowpath_topaz_id` instead of a second `topaz_id` column.

The result is a tighter runtime contract between Peridot and WEPPpy: failed output writes stop automation with a non-zero exit, and sub-field flowpath metadata can be consumed without parser-specific duplicate-header behavior.

## Progress

- [x] (2026-04-26 22:51 UTC) Package scaffold created in WEPPpy with package brief, tracker, active ExecPlan, and compatibility/regression artifact.
- [x] (2026-04-26 22:51 UTC) Initial source audit confirmed current CLI result-discard pattern and duplicate `field_flowpaths.csv` header source.
- [x] (2026-04-26 23:07 UTC) Designed and added Peridot regression coverage for CLI error propagation.
- [x] (2026-04-26 23:07 UTC) Implemented Peridot CLI result propagation in `abstract_watershed` and `wbt_abstract_watershed`.
- [x] (2026-04-26 23:07 UTC) Added Peridot regression coverage for unique field-flowpath CSV headers.
- [x] (2026-04-26 23:07 UTC) Implemented Peridot `field_flowpaths.csv` header disambiguation.
- [x] (2026-04-26 23:07 UTC) Added WEPPpy compatibility tests for new and historical field-flowpath CSV schemas.
- [x] (2026-04-26 23:07 UTC) Implemented WEPPpy normalization to canonical `flowpath_topaz_id`.
- [x] (2026-04-26 23:07 UTC) Updated Peridot and WEPPpy docs.
- [x] (2026-04-26 23:07 UTC) Ran validation and recorded artifacts.
- [x] (2026-04-27 01:26 UTC) Revalidated Peridot full `cargo test` after commit `e09f54c`; earlier support/raster full-suite failures are closed.

## Surprises & Discoveries

- Observation: Peridot release binaries under `target/release/` are already dirty in the local worktree.
  Evidence: `git status --short` in `/home/workdir/peridot` reports modified `target/release/abstract_watershed` and `target/release/wbt_abstract_watershed` before implementation.

- Observation: WEPPpy currently reads `field_flowpaths.csv` with pandas and writes `field_flowpaths.parquet` without explicitly handling the duplicate second `topaz_id` column.
  Evidence: `/workdir/wepppy/wepppy/topo/peridot/peridot_runner.py::post_abstract_sub_fields` reads the CSV, casts `topaz_id` and `fp_id`, then writes Parquet.

- Observation: Filesystem-permission-based CLI tests would be brittle in this environment because tests may run as root or in containers with different permission semantics.
  Evidence: The implemented CLI regression tests inject failing abstraction closures and assert returned `io::Error` propagation instead of depending on chmod behavior.

- Observation: The earlier Peridot support interpolation panic-expectation failures and raster fixture/GDAL open failures were real loose ends before benchmark work, but they are no longer open.
  Evidence: Peridot commit `e09f54c` (`Fix Peridot full-suite regressions`) is present locally, and `cargo test` in `/home/workdir/peridot` passes unit, bin, integration, and doctest suites.

## Decision Log

- Decision: Keep parent `topaz_id` and rename the duplicate flowpath record column to `flowpath_topaz_id`.
  Rationale: WEPPpy already uses `topaz_id` as the parent hillslope/subcatchment ID. Renaming only the duplicate column fixes ambiguity with the smallest downstream compatibility impact.
  Date/Author: 2026-04-26 / Codex.

- Decision: Normalize historical pandas-mangled `topaz_id.1` in WEPPpy rather than migrating old run files.
  Rationale: The package should make new and post-processing behavior safe without mutating historical run artifacts under `/wc1/runs`.
  Date/Author: 2026-04-26 / Codex.

- Decision: Keep Peridot binary rebuild/deployment out of the package unless explicitly requested.
  Rationale: The requested fixes are source/test/docs changes. Existing dirty release binaries are unrelated and should not be staged accidentally.
  Date/Author: 2026-04-26 / Codex.

## Outcomes & Retrospective

Completed 2026-04-26. Peridot CLI wrappers now return the underlying abstraction `io::Result<()>`, which makes propagated abstraction errors visible to process status. `field_flowpaths.csv` now has unique headers with `flowpath_topaz_id`, and WEPPpy normalizes both new and historical CSV forms before writing canonical Parquet.

The main design point was compatibility: preserving parent `topaz_id` avoided unnecessary downstream churn, while canonicalizing the old pandas `topaz_id.1` name prevents historical duplicate-header behavior from leaking into current Parquet contracts. The CLI regression uses injected abstraction failures because that tests the wrapper contract directly without relying on environment-specific filesystem failure behavior.

## Context and Orientation

There are two repositories in scope.

In `/home/workdir/peridot`, `src/bin/abstract_watershed.rs` and `src/bin/wbt_abstract_watershed.rs` are command-line entrypoints. Each parses CLI flags, builds a Rayon thread pool, calls the underlying abstraction function, and currently assigns the returned result to `_` before returning `Ok(())`. That means an `io::Error` returned by the abstraction function can be discarded by the CLI process.

In `/home/workdir/peridot`, `src/watershed_abstraction/flowpath_collection.rs::write_field_subflows_metadata_to_csv` writes the `field_flowpaths.csv` header. It currently writes two columns named `topaz_id`: the first is the parent hillslope/subcatchment ID resolved from `fake_topaz_id_lookup`; the second is the topaz ID stored on the individual flowpath record.

In `/workdir/wepppy`, `wepppy/topo/peridot/peridot_runner.py::post_abstract_sub_fields` reads `ag_fields/sub_fields/field_flowpaths.csv`, casts `topaz_id` and `fp_id`, writes `field_flowpaths.parquet`, and removes the CSV. It must learn the new `flowpath_topaz_id` column while still accepting historical CSVs where pandas names the duplicate second header `topaz_id.1`.

The compatibility plan is recorded in `docs/work-packages/20260426_peridot_runtime_contract_hardening/artifacts/2026-04-26_compatibility_regression_plan.md` and is normative for this package.

## Plan of Work

Milestone 1 hardens Peridot CLI error propagation. First design regression coverage that observes a non-zero exit or returned error for a propagated write-stage failure. Then update both CLI entrypoints to propagate the abstraction result with `?` instead of discarding it. The likely implementation is to change each `main` return type to `std::io::Result<()>` or `Result<(), Box<dyn std::error::Error>>`, remove unused `GdalError` imports if no longer needed, call the abstraction function with `?`, and return `Ok(())` only after success.

Milestone 2 fixes the Peridot field-flowpath CSV header. Add or update a test that writes a representative field-flowpath CSV and asserts that headers are unique and include `field_id`, `topaz_id`, `sub_field_id`, `flowpath_topaz_id`, and `fp_id` in order. Then update `write_field_subflows_metadata_to_csv` to use `flowpath_topaz_id` for the fourth column.

Milestone 3 updates WEPPpy compatibility normalization. Add targeted tests around `post_abstract_sub_fields` or a new helper it uses. The helper should normalize `topaz_id.1` to `flowpath_topaz_id` when needed, reject ambiguous mixed inputs, cast numeric columns consistently, and write canonical Parquet.

Milestone 4 updates documentation. Peridot output contract and migration docs should no longer state that duplicate `topaz_id` headers are current behavior. WEPPpy AgFields/data-table docs should describe the canonical `field_flowpaths.parquet` schema where appropriate.

Milestone 5 runs validation. Capture command outputs in an artifact and update tracker/package closure notes.

## Concrete Steps

Start in Peridot:

    cd /home/workdir/peridot
    git status --short
    rg -n "let _ = abstract_watershed|let _ = wbt_abstract_watershed|field_flowpaths|topaz_id\.1|flowpath_topaz_id" src tests docs

Implement CLI result propagation and tests. Then implement CSV header change and tests.

Move to WEPPpy:

    cd /workdir/wepppy
    rg -n "field_flowpaths|post_abstract_sub_fields|topaz_id\.1|flowpath_topaz_id" wepppy tests docs

Implement compatibility normalization and targeted tests. Update docs and work-package artifacts.

## Validation and Acceptance

Validation commands run:

    cd /home/workdir/peridot
    cargo test --test watershed_parquet_manifest --test field_flowpaths_schema --bin abstract_watershed --bin wbt_abstract_watershed
    cargo test
    git diff --check

    cd /workdir/wepppy
    wctl run-pytest tests/topo/test_peridot_runner_wait.py tests/topo/test_peridot_sub_fields_schema.py
    wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_runtime_contract_hardening
    git diff --check

Acceptance was met with targeted Rust, pytest, doc-lint, and whitespace checks. Broad Peridot `cargo test` was also attempted and failed in unrelated library tests documented in the validation artifact. Broad WEPPpy tests were not run because the package only touched Peridot runner normalization and docs; existing package guidance allowed targeted validation, and the broader suite has known unrelated blockers from active packages.

Follow-up validation on 2026-04-27 closed the broad Peridot test-suite risk. After Peridot commit `e09f54c`, `cargo test` passes across library, CLI-wrapper, integration, and doctest suites. This makes the Peridot side acceptable as a benchmark-work prerequisite; the remaining benchmark risk is rediscovering whether the stale WEPPpy Python abstraction still runs.

## Idempotence and Recovery

The implementation is source/test/docs only. Do not stage Peridot `target/release/*` binaries unless the user explicitly adds deployment scope. If a test fixture creates temporary run directories, ensure it uses a temp path and deletes it after test completion. If a schema-normalization helper is introduced in WEPPpy, keep it deterministic and side-effect free so tests can exercise it without requiring a full WEPPpy run.

If implementation partially lands, recover by reverting only the incomplete local edits from this package, not unrelated dirty files. Keep the compatibility plan intact and update tracker notes with exact remaining work.

## Artifacts and Notes

Required artifacts:

- `artifacts/2026-04-26_compatibility_regression_plan.md` exists before implementation.
- Add `artifacts/<date>_validation_summary.md` during implementation with command results.
- Add review disposition artifacts if code review finds medium/high issues.

## Interfaces and Dependencies

Peridot interfaces:

- `src/bin/abstract_watershed.rs::main`
- `src/bin/wbt_abstract_watershed.rs::main`
- `src/watershed_abstraction/flowpath_collection.rs::write_field_subflows_metadata_to_csv`

WEPPpy interfaces:

- `wepppy/topo/peridot/peridot_runner.py::post_abstract_sub_fields`
- Any helper extracted for field-flowpath schema normalization

The canonical CSV/Parquet field-flowpath columns after implementation should include:

    field_id, topaz_id, sub_field_id, flowpath_topaz_id, fp_id,
    slope_scalar, length, width, direction, aspect, area, elevation,
    order, centroid_px, centroid_py, centroid_lon, centroid_lat

## Revision Notes

- 2026-04-26 / Codex: Initial ExecPlan authored for Peridot CLI error propagation and sub-field CSV schema hardening package.
- 2026-04-26 / Codex: Completed implementation, validation, docs, and package closeout; plan archived to `prompts/completed/`.
- 2026-04-27 / Codex: Added post-close validation note that Peridot full `cargo test` now passes after commit `e09f54c`, closing the previously recorded support/raster loose ends.
