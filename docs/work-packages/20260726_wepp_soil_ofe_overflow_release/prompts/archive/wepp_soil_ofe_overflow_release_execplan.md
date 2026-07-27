# Repair watershed SOIL OFE overflow and release WEPP 260726

This ExecPlan is maintained under
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, watersheds with more than 99 hillslopes produce parseable SOIL
output using `wepp_260726`, while already-generated files containing `**`
remain recoverable through strict ordered reconstruction. WEPPpy vendors the
model and native releases needed to finish post-processing.

## Progress

- [x] (2026-07-27) Confirmed the incident signature and fixed-width root cause.
- [x] (2026-07-27) Scaffolded the three-repository work package.
- [x] (2026-07-27) Audited WEPP build/release and WEPPpy vendoring contracts.
- [x] (2026-07-27) Widened the WEPP SOIL OFE field and generated incident output.
- [x] (2026-07-27) Implemented strict WEPPpyo3 historical overflow reconstruction.
- [x] (2026-07-27) Built and validated WEPP and WEPPpyo3 release artifacts.
- [x] (2026-07-27) Vendored `wepp_260726` in WEPPpy and ran integration gates.
- [x] (2026-07-27) Committed and pushed all three repositories and closed the package.

## Surprises & Discoveries

- Observation: The first `**` is OFE 100 and each day contains 238 rows.
  Evidence: Incident lines 7-244 cover day 1; day 2 restarts at line 245.
- Observation: WEPP source uses `1x,i2,2x,i3,2x,i5` for SOIL records.
  Evidence: `src/watbal.for` and `src/watbal_hourly.for`.
- Observation: The synced run had legacy pass files but no HBP shards.
  Evidence: The first exact-release replay stopped before simulation; regenerating
  587/587 shards with the paired hillslope binary resolved the fixture mismatch.
- Observation: The canonical smoke fixture is absent on this host.
  Evidence: Both smoke helper invocations reported missing
  `/wc1/runs/du/dumbfounded-patentee` inputs.

## Decision Log

- Decision: Produce both a model-output repair and a parser compatibility path.
  Rationale: Future output must preserve identity directly, while the synced
  incident output is otherwise valid and expensive to rerun.
  Date/Author: 2026-07-27, Codex.
- Decision: Require file-internal ordering evidence before reconstructing `**`.
  Rationale: The marker carries no identifier; accepting it without sequence
  invariants would silently corrupt `wepp_id`.
  Date/Author: 2026-07-27, Codex.

## Outcomes & Retrospective

The future producer and historical consumer are both repaired. Generated
`wepp_260726` output preserves numeric OFEs through 238, while the native parser
recovers all 521,696 historical incident rows under strict daily invariants.
The model and native artifacts are release-ready and WEPPpy vendors the exact
model binaries.

## Context and Orientation

WEPP fixed-form sources in
`/workdir/wepp-forest_260430_baseline/src/watbal.for` and
`watbal_hourly.for` write watershed SOIL rows. WEPPpyo3 parses them in
`/workdir/wepppyo3/wepp_interchange/src/soil.rs`. WEPPpy selects vendored
binaries from `wepp_runner/bin` and records dated-binary behavior through
sidecars and binary lifecycle documentation.

## Plan of Work

First inventory the dated-release script and current vendored sidecar contract.
Change only the OFE integer width in both WEPP output sites, then add a
regression that runs a greater-than-99-OFE case and checks numeric boundary
rows.

In WEPPpyo3, parse the fixed-width OFE marker separately from measurements and
maintain a per-day sequence validator. Numeric-only files remain unchanged.
Legacy `**` begins only after 99, reconstructs contiguous IDs, and must repeat a
stable complete daily layout. Add focused Rust failures and run the synced
incident conversion using the rebuilt release extension.

Run every mandatory WEPP release gate before generating `wepp_260726` and its
hillslope companion. Vendor both into WEPPpy, update provenance/sidecars, and
run host/container smoke plus runner and interchange tests.

## Validation and Acceptance

Acceptance requires generated output from the rebuilt WEPP binary, successful
native conversion of the existing incident file, verified binary and shared
object hashes, and clean remote commits in all three repositories.

## Idempotence and Recovery

Build outputs are reproducible and dated artifacts do not replace historical
binaries. Test conversion writes temporary parquet. No production run or
deployment is mutated.
