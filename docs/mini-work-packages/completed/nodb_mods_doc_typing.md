# NoDb Mods Documentation & Typing Tracker

> Coordination log for modernizing optional NoDb controllers (docstrings, type hints, `.pyi` stubs, validation).

Date: 2025-10-22

## Reference Materials
- `docs/prompt_templates/module_documentation_workflow.prompt.md`
- `docs/prompt_templates/AGENTS.md`
- `TYPE_HINTS_SUMMARY.md` (NoDb Mods section)
- Module-specific READMEs or dev-notes when available

## Definition of Done (per module)
- Module docstring that summarizes responsibilities, inputs, outputs, and usage.
- All public functions/methods annotated; class-level constants typed.
- `.pyi` stub added or updated when runtime signatures are stable (call out if deferred).
- Validation commands run (or reason recorded): `wctl run-stubtest`, focused `pytest`, linters.
- `TYPE_HINTS_SUMMARY.md` and this tracker updated with status and notes.

## Status Table
| Module | Docstring | Type Hints | `.pyi` | Owner | Notes |
| --- | --- | --- | --- | --- | --- |
| `wepppy/nodb/mods/disturbed/disturbed.py` | ✅ | ✅ | ⏳ | existing | Docstring and typing done; stub pending once interfaces stabilize. |
| `wepppy/nodb/mods/path_ce/path_cost_effective.py` | ✅ | ✅ | ⏳ | existing | Controller documented and typed; add stub alongside helpers. |
| `wepppy/nodb/mods/path_ce/data_loader.py` | ✅ | ✅ | ⏳ | existing | Typed utility; stub to follow PathCE controller. |
| `wepppy/nodb/mods/path_ce/path_ce_solver.py` | ✅ | ✅ | ⏳ | existing | Fully typed/documented; ready for `.pyi`. |
| `wepppy/nodb/mods/omni/omni.py` | ✅ | ✅ | ✅ | lead | Module docstring, typing, and `omni.pyi` delivered; stubtest now part of the validation routine. |
| `wepppy/nodb/mods/ag_fields/ag_fields.py` | ✅ | ✅ | ✅ | lead | Docstring, typing, and `ag_fields.pyi` added; stubtest executed via `wctl`. |
| `wepppy/nodb/mods/ash_transport/ash.py` | ✅ | ✅ | ✅ | lead | Docstring, typing, and `ash.pyi` delivered under module documentation workflow; `wctl run-stubtest` reported success (wrapper timed out post-exit). |
| `wepppy/nodb/mods/baer/baer.py` | ✅ | ✅ | ✅ | lead | Docstring + full annotations landed, `baer.pyi` added, stubtest run (wctl reported success before timeout). |
| `wepppy/nodb/mods/rangeland_cover/rangeland_cover.py` | ✅ | ✅ | ✅ | lead | Module docstring, full annotations, and `rangeland_cover.pyi` added; stubtest validated via `wctl`. |
| `wepppy/nodb/mods/rap/rap.py` | ✅ | ✅ | ✅ | lead | Module docstring, typing, and `rap.pyi` shipped; stubtest pending container availability. |
| `wepppy/nodb/mods/rap/rap_ts.py` | ✅ | ✅ | ✅ | lead | Docstring + annotations complete, `rap_ts.pyi` added, and `wctl run-stubtest` recorded (iterator now emits latest-year single-OFE cover). |
| `wepppy/nodb/mods/revegetation/revegetation.py` | ✅ | ✅ | ✅ | lead | Docstring + annotations complete, `revegetation.pyi` synced, `wctl run-stubtest` recorded (library scenarios now documented for RAP_TS consumers). |
| `wepppy/nodb/mods/shrubland/shrubland.py` | ✅ | ✅ | ✅ | lead | Docstring + annotations complete, `shrubland.pyi` synced, `wctl run-stubtest` recorded (outputs now described for UI dashboards). |
| `wepppy/nodb/mods/treatments/treatments.py` | ⛔️ | ⚠️ | ⛔️ | — | Some annotations; needs docstring and completion. |
| `wepppy/nodb/mods/treecanopy/treecanopy.py` | ✅ | ✅ | ✅ | lead | Docstring + annotations complete, `treecanopy.pyi` synced, `wctl run-stubtest` recorded (single-layer canopy summaries documented for dashboards). |
| `wepppy/nodb/mods/debris_flow/debris_flow.py` | ✅ | ✅ | ✅ | lead | Docstring + annotations complete, `debris_flow.pyi` synced, `wctl run-stubtest` recorded (precip matrices now typed for dashboard consumers). |
| `wepppy/nodb/mods/rhem/rhem.py` | ✅ | ✅ | ✅ | lead | Module docstring, typing, and `rhem.pyi` added; `wctl run-stubtest wepppy.nodb.mods.rhem.rhem` succeeded (post-container restart). |

Legend: ✅ complete, ⚠️ partial, ⛔️ missing, ⏳ pending

## Action Log
- _2025-XX-XX_: Tracker created. Disturbed + PathCE marked as documented/typed; stub work deferred.
- _2025-XX-XX_: BAER modernized (docstring, type hints, `baer.pyi`); stubtest executed via `wctl run-stubtest`.
- _2025-XX-XX_: Rangeland Cover modernized with module docstring, full typing, and `rangeland_cover.pyi`; stubtest executed via `wctl`.
- _2025-XX-XX_: Ash Transport modernized (docstring, type hints, `ash.pyi`); `wctl run-stubtest wepppy.nodb.mods.ash_transport.ash` completed successfully.
- _2025-XX-XX_: RAP modernized with module docstring, typing, and `rap.pyi`; stubtest pending container availability.
- _2025-XX-XX_: RHEM modernized (docstring, type hints, `rhem.pyi`); stubtest executed via `wctl run-stubtest wepppy.nodb.mods.rhem.rhem`.
- _2025-XX-XX_: Omni modernized (docstring, type hints, `omni.pyi`); `wctl run-stubtest wepppy.nodb.mods.omni.omni` verified runtime/stub parity.
- _2025-XX-XX_: AgFields modernized (docstring, type hints, `ag_fields.pyi`); stubtest executed via `wctl run-stubtest wepppy.nodb.mods.ag_fields.ag_fields`.
- _2025-XX-XX_: RAP_TS modernized (docstring, full typing, `rap_ts.pyi`); stubtest executed via `wctl run-stubtest wepppy.nodb.mods.rap.rap_ts`.
- _2025-XX-XX_: Revegetation modernized (docstring, full typing, `revegetation.pyi`); stubtest executed via `wctl run-stubtest wepppy.nodb.mods.revegetation.revegetation`.
- _2025-XX-XX_: Shrubland modernized (docstring, full typing, `shrubland.pyi`); stubtest executed via `wctl run-stubtest wepppy.nodb.mods.shrubland.shrubland`.
- _2025-XX-XX_: Debris Flow modernized (docstring, full typing, `debris_flow.pyi`); stubtest executed via `wctl run-stubtest wepppy.nodb.mods.debris_flow.debris_flow`.
- _2025-XX-XX_: TreeCanopy modernized (docstring, full typing, `treecanopy.pyi`); stubtest executed via `wctl run-stubtest wepppy.nodb.mods.treecanopy.treecanopy`.

## Next Steps
1. Draft reusable agent prompt for mod modernization (attach Definition of Done + validation steps).
2. Prioritize next targets (suggest remaining wildfire analytics mods and supporting utilities).
3. Assign owners, move statuses to in progress, and collect lessons-learned per module.
