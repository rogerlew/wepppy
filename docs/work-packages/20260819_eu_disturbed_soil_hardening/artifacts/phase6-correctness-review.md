# Phase 6 Independent Correctness Review

**Date**: 2026-08-19
**Reviewer**: Herschel (`01a01c0a-5f4b-73c3-97d0-9799b4919a6b`)
**Scope**: Read-only review of the EU-specific runtime gate, provenance
marker, quality-report parser, single-OFE/MOFE publication paths, and
regression tests.

## Findings and disposition

| Severity | Finding | Disposition | Evidence |
| --- | --- | --- | --- |
| P1 | Partial or empty quality reports could be discovered after earlier publication or bypass a channel-only run. | **Fixed** | Runtime entry points preflight required non-channel TopoAZ coverage with `source.quality_report.coverage_incomplete`; the low-level parser still permits an empty accepted report for serialization round-trip compatibility. |
| P2 | A direct `modify_soil()` caller could omit the report and bypass the EU gate. | **Fixed** | Marked ESDAC calls now load the report inside `modify_soil()` when no carrier is supplied. |
| P2 | Report `soil_key` was ignored, allowing stale quality evidence to be applied to a remapped base soil. | **Fixed** | `SoilQualityResult` carries the additive key; the report parser preserves it and runtime checks it against `domsoil_d` before generation. |
| P2 | MOFE failures could leave already-published artifacts. | **Fixed** | The MOFE wrapper snapshots existing `.sol` files, restores them, and removes files created by a failed operation before re-raising. |
| P3 | Provenance classification used a broad EU module prefix. | **Fixed** | The marker is set only for the exact `wepppy.eu.soils.build_esdac_soils` builder identity; other builders remain unmarked. |
| P1 | Reused single-OFE outputs referenced uninitialized `disturbed_fn` and `replacements`. | **Fixed** | These values are initialized before the create/reuse branch; the runtime test invokes the same location twice. |
| P2 | A degraded report entry with no diagnostics was accepted. | **Fixed** | The report parser rejects degraded entries without diagnostics as `source.quality_report.outcome_mismatch`. |
| P2 | MOFE rollback did not cover a preexisting segment file. | **Fixed** | The rollback snapshot now covers all existing `.sol` files, not only final `.mofe.sol` files. |
| P1 | MOFE rollback restored files but not in-memory `domsoil_d`, `soils`, or area/coverage state. | **Fixed** | The transaction wrapper snapshots and restores controller state as well as files; the regression verifies mappings, summaries, and metrics. |
| P2 | Report `accepted_count` and `rejected_count` were not validated against profile outcomes. | **Fixed** | The carrier loader validates nonnegative integer counts and exact outcome totals. |
| P2 | Single-OFE report keys were checked only as each location was reached. | **Fixed** | Single-OFE preflight now checks coverage and every `soil_key` against `domsoil_d` before the write loop. |
| P2 | Single-OFE batch failures could leave earlier artifacts and NoDb mappings published. | **Fixed** | The single-OFE operation now snapshots/restores `.sol` files, `domsoil_d`, soil summaries, and area/coverage metrics; a failure regression covers the rollback. |
| P2 | Required report diagnostics and schema version types were not fully enforced. | **Fixed** | Missing `diagnostics` is malformed and boolean `schema_version` values are rejected; both cases have regression coverage. |
| P2 | Rollback errors could mask the original operation failure or skip cleanup. | **Fixed** | Shared single/MOFE transaction handling captures narrow rollback errors, logs them, reports an explicit rollback failure, and always removes the backup directory. |

The reviewer returned the findings above after the first implementation pass.
The fixes were applied in the working tree and re-reviewed; no remaining P1,
P2, or P3 finding was reported in the final follow-up review.

The final independent follow-up by Herschel returned **No findings** after the
single-OFE transaction boundary and structural carrier checks were added.

## Review evidence

- Runtime and persistence tests: `50 passed, 2 warnings` in the final focused
  set.
- EU/disturbed/root-Soils combined suite after the first fix set:
  `139 passed, 20 skipped, 2 warnings`; the final focused set additionally
  covers report outcome/count mismatch, NoDb marker reload, and controller
  state rollback for both MOFE and single-OFE operations.
- Changed-file broad-exception enforcement: passed with zero net delta.
- Python compilation and `git diff --check`: passed.

## Residual review notes

The runtime gate is intentionally EU/ESDAC-specific. Non-EU builders do not
carry the marker and retain existing Disturbed behavior. The quality report is
validated before runtime publication, while the report parser remains a
reusable low-level carrier loader and therefore permits an empty accepted
profile list until a runtime caller supplies required location coverage.
