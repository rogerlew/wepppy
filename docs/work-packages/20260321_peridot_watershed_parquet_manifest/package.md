# Peridot Watershed Parquet + Manifest Integration

**Status**: Completed (2026-03-21)

## Overview
This package upgrades the Peridot-to-WEPPpy watershed abstraction contract so Peridot writes first-class parquet outputs directly and ships a run-generated `watershed/README.md` manifest/schema summary. WEPPpy then consumes these parquet files directly for new runs while keeping explicit legacy behavior for older runs that only have CSV outputs.

## Objectives
- Enable Peridot `abstract_watershed` and `wbt_abstract_watershed` to write complete watershed parquet outputs (`hillslopes`, `channels`, optional `flowpaths`).
- Generate `watershed/README.md` from Peridot with executed flags, file manifest, and tabular schema summaries.
- Remove mandatory CSV->parquet conversion from WEPPpy for new runs while preserving explicit legacy compatibility for old runs.
- Add and pass focused Rust and pytest coverage for direct parquet and legacy fallback paths.
- Validate on real run `/wc1/runs/un/unassailable-sensuousness` including slope/profile sanity checks.

## Scope

### Included
- Peridot Rust abstraction pipeline updates and tests.
- WEPPpy integration updates for direct parquet-first consumption.
- Documentation updates for changed contracts/behavior.
- Work-package artifacts including subagent review outputs and validation summary.

### Explicitly Out of Scope
- Large redesigns of watershed abstraction algorithms unrelated to output format/manifest.
- Backfilling historical runs to regenerate data unless required for explicit verification.
- Unrelated WEPP output/reporting refactors.

## Stakeholders
- **Primary**: WEPPpy maintainers and operators running watershed abstraction workflows.
- **Reviewers**: User/requester and AI subagent reviewers (`reviewer`, `test_guardian`).
- **Informed**: Downstream tooling relying on watershed parquet contracts.

## Success Criteria
- [x] Peridot writes `watershed/hillslopes.parquet`, `watershed/channels.parquet`, and conditional `watershed/flowpaths.parquet` in both abstraction paths.
- [x] Peridot writes `watershed/README.md` with flag-aware manifest/schema details.
- [x] WEPPpy uses Peridot parquet directly for new runs without mandatory CSV->parquet conversion.
- [x] WEPPpy retains explicit legacy behavior for runs lacking parquet.
- [x] Required Rust + pytest + real-run validation commands pass and are documented.
- [x] Review artifacts exist under `artifacts/` and resulting high/medium issues are resolved or explicitly accepted.

## Dependencies

### Prerequisites
- Existing Peridot abstraction outputs and schema expectations in WEPPpy.
- Working `wctl` environment for targeted pytest.
- Access to `/wc1/runs/un/unassailable-sensuousness` for runtime verification.

### Blocks
- Future cleanup package removing remaining CSV legacy code after migration adoption.

## Related Packages
- **Depends on**: None.
- **Related**: `docs/work-packages/20260305_terrain_processor_implementation/` (watershed processing context).
- **Follow-up**: Potential package to retire legacy CSV fallback once historical run migration is complete.

## Timeline Estimate
- **Expected duration**: 1-3 days.
- **Complexity**: High.
- **Risk level**: Medium-High (cross-repo schema contract and runtime-path integration).

## References
- `docs/prompt_templates/codex_exec_plans.md` - ExecPlan requirements.
- `AGENTS.md` - repo-wide execution constraints.
- `/workdir/peridot` watershed abstraction modules - parquet/manifest implementation target.
- `wepppy/nodb` watershed integration modules - direct parquet consumption target.

## Deliverables
- Peridot code + tests for parquet outputs and generated `watershed/README.md`.
- WEPPpy integration/test/doc updates for parquet-first with explicit legacy fallback.
- Work-package execution artifacts (review + validation).

## Follow-up Work
- Evaluate eventual deprecation timeline for CSV compatibility once old-run coverage window closes.
- Add end-to-end Peridot abstraction entrypoint tests (topaz + wbt) for output wiring regression protection.
- Evaluate chunked/row-group flowpaths parquet writer to reduce remaining peak-memory risk on large flowpath exports.
