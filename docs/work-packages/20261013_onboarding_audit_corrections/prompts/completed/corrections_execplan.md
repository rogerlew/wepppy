# Apply selected onboarding audit corrections

Maintain this ExecPlan under docs/prompt_templates/codex_exec_plans.md.

## Purpose and context

The operator selected D01/D02/D13/D14/D18 from docs/investigations/20261013_primary_onboarding_audit/dispositions.md. The current SBS sanity check rejects entirely unknown palettes even though SoilBurnSeverityMap supports unassigned classes. New agricultural projects select wepp_260714 despite the operator selecting wepp_261010. Documentation also needs explicit ORCID deferral, an internal-access contact and an official FAQ title.

## Progress

- [x] Inspect current behavior and capture operator decisions.
- [x] Review and commit contract checkpoint.
- [x] Implement bounded changes and regressions.
- [x] Validate artifacts, update dispositions and close out.

## Plan of work and milestones

First amend SBS raster/upload contracts and ADR provenance; obtain two independent read-only reviews and commit the checkpoint before production edits. Next change only shared palette admission logic, preserving native classification and existing validity checks; update focused tests with synthetic actual GeoTIFFs and inspect unknown-class output and subsequent explicit remapping. Update the requested AgFields literal, matching help/docs, and selected onboarding prose. Finally run targeted wctl tests, docs lint and config readback, review the diff, and record exact limitations and outstanding audit items.

## Validation and acceptance

Use wctl run-pytest for tests/nodb/mods/baer/test_sbs_map_extended.py, native SBS suites and affected upload tests. Unrecognized palettes must pass admission, retain unknown labels and export those pixels as existing NoData until mapped. Mixed palettes preserve known classes; no palette retains numeric classification. Invalid projection, noninteger raster and excess classes still fail. Native dependency/computation errors still fail. Read the requested config with its existing parser; no new tests merely pin its literal. Do not claim a full AgFields model validation for a config-value edit.

## Compatibility and regression plan

No persisted keys or raster format changes. Existing recognized palettes, numeric maps, explicit NoData masks and saved executable selections remain. The only admitted additional state is a structurally valid palette with zero recognized burn colors. Preserve the current unassigned sentinel and validate native exported pixels, then explicitly assign a color and verify the fresh exported artifact changes. Existing malformed/hostile file and route checks remain. No queue wiring or upload path policy changes.

## Surprises & Discoveries

The existing classifier already supports unknown colors; admission was stricter than the supported interactive correction path. The native palette summary's color_table_valid describes recognition, not raster structural validity. ADR-0045 distinguishes visible Unassigned from source NoData; model exports retain 255. A test assumption about numeric source-NoData display entries was corrected to the existing nv encoding, with no producer change.

## Decision Log

2026-10-13, operator: choose wepp_261010 for new AgFields projects; unknown colors stay unassigned; defer ORCID indefinitely; request access through Mariana Dobre (mdobre@uidaho.edu); make FAQ official. Restrict execution to these selected dispositions. Runtime ORCID removal is not requested.

## Outcomes & Retrospective

Implemented selected D01/D02/D13/D14/D18 after checkpoint b4be200b4. Final focused validation: 182 passed/1 skipped with direct native raster artifact assertions; config readback and documentation/catalog checks pass. Other 13 audit dispositions remain open. No production rollout or new AgFields scientific validation claimed.

## Recovery and dependencies

Use the existing wepppyo3 native implementation and GDAL, not an alternate raster engine. Reverting the admission conditional restores the previous rejection; no migration is required. Reverting the config default affects subsequent new projects only. Work remains on master with no production deployment. Retain evidence in this package and update tracker before handoff.
