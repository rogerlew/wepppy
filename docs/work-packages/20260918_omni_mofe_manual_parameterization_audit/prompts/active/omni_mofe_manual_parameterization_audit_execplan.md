# Audit Omni MOFE scenarios against manual Modify Landuse

This ExecPlan is a living document and follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This package gives operators an evidence-backed answer to whether the completed `ventilated-gag` Omni scenarios behave like the manual Modify Landuse workflow on a non-continental-US MOFE configuration. It compares persisted assignments and generated outputs without changing production, and it explicitly identifies when a result cannot be treated as a like-for-like comparison.

## Progress

- [x] (2026-09-18) Confirm production host and run path; inventory six Omni children and parent configuration.
- [x] (2026-09-18) Capture read-only NoDb, parquet, README, and representative generated artifacts with host SHA256 evidence.
- [x] (2026-09-18) Read and map the manual `Landuse.modify()` MOFE behavior and Omni treatment definitions.
- [x] (2026-09-18) Generate and review the comparison CSV and rank/tolerance checks.
- [x] (2026-09-18) Finish `audit.md`, validate docs, and record outcome/disposition.

## Surprises & Discoveries

- `uniform_low` and `uniform_moderate` persisted different management IDs and soil descriptions, but their watershed metrics are identical in all inspected measures.
- The run's Omni configuration selects only `thinning_40_75` and `thinning_65_85`; the manual treatment catalog contains more thinning combinations.
- MOFE state covers 455 hillslopes and 1,065 OFE segments; manual modification rewrites every OFE segment for each selected hillslope.

## Decision Log

- Decision: Treat this as a read-only production audit; do not create manual scenarios or rerun WEPP. Rationale: the user requested comparison and disposition, and production mutations would confound the captured baseline. Date/Author: 2026-09-18, Codex.
- Decision: Use 20% and rank-order expectations as diagnostics, not byte-equality gates. Rationale: the user explicitly rejects byte precision while requiring directional consistency. Date/Author: 2026-09-18, Codex.
- Decision: Classify identical low/moderate outputs as investigate rather than accepted variance. Rationale: distinct persisted parameterization with no output separation fails the requested severity signal. Date/Author: 2026-09-18, Codex.

## Outcomes & Retrospective

The audit is complete. It found an exact low/moderate output equality despite distinct persisted severity classes, and a separate prescribed-fire application split (21 of 455 hillslopes) that requires a controlled reproduction before any production change. Thinning catalog differences are accepted scope differences. No production mutation was performed.

## Context and Orientation

Omni clones a parent run under `_pups/omni/scenarios/<name>` and applies scenario-specific disturbed/landuse/soil settings before running WEPP. The manual Modify Landuse endpoint ultimately calls `Landuse.modify(topaz_ids, landuse)`. In MOFE mode that method validates all assignment segments, changes the selected hillslope's dominant class and every OFE segment, rebuilds multiple-OFE inputs, and refreshes management cover defaults. This package compares those contracts and the resulting artifacts, not browser screenshots.

## Plan of Work

Use the captured raw files to produce one CSV of scenario metrics, assignment counts, management parameters, and hashes. Review the source implementation and scenario documentation for differences in scope, selection, and treatment options. Disposition each discrepancy as accepted workflow difference, investigate, or confirmed error only when evidence proves it. Keep all production actions read-only.

## Concrete Steps

From the repository root, run `python3 docs/work-packages/20260918_omni_mofe_manual_parameterization_audit/scripts/audit_compare.py`, then inspect the CSV and `audit.md`. Run `wctl doc-lint` against all Markdown files in this package.

## Validation and Acceptance

Acceptance requires a reproducible CSV, documented source paths and hashes, explicit treatment-option differences, a low/moderate/high metric comparison, rank-order assessment, and a disposition for every material discrepancy. No production write or rerun may appear in the evidence.

## Idempotence and Recovery

The analysis script only reads package-local captures and overwrites its derived CSV. Re-running it is safe. Production evidence must be recollected as a new dated capture if the run changes; never overwrite historical raw evidence silently.

## Artifacts and Notes

The raw evidence directory contains copies of production files and representative generated artifacts. Host paths and SHA256 values are recorded in `audit.md`.

## Interfaces and Dependencies

The script uses Python's standard library against a CSV export of the captured Parquet file. It does not import or mutate NoDb controllers.
