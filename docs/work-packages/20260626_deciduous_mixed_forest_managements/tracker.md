# Tracker — Deciduous and Mixed Forest Management Types

**Status**: Implemented; targeted QA passed. Authored by Claude Code 2026-06-26.

## Key facts established at scaffold time

- `disturbed.json` keys `41` (Deciduous), `42` (Evergreen), `43` (Mixed) all
  currently resolve to `UnDisturbed/Old_Forest.man` (evergreen `Tah_4899`,
  no senescence/decomposition, all phenology dates `0`).
- `disturbed_land_soil_lookup.csv` is keyed `(luse, stext)`; `luse` matches the
  JSON `DisturbedClass`. It carries plant-canopy override columns `xmxlai`,
  `plant.data.decfct`, `plant.data.dropfc`, plus `rdmax`, `pmet_kcb`. The current
  `forest` rows use `xmxlai=14, rdmax=2, decfct=1, dropfc=1, pmet_kcb=0.95`.
- Canopy override path: `wepppy/nodb/core/wepp_prep_service.py`
  (`plant_data.ln *= cancov_override`, `management.set_ln`) and
  `wepppy/nodb/core/management_overrides.resolve_disturbed_scalar_replacements`.
- wepppy mandates a parameterization ADR (`docs/adrs/ADR-0002`); standard at
  `docs/standards/parameterization-adr-standard.md`; this package uses
  `docs/adrs/ADR-0009-deciduous-mixed-forest-managements.md`.

## Checklist

- [x] `parameterization-research.md` (cited authority, value justification)
- [x] `Deciduous_Forest.man` authored + parses
- [x] `Mixed_Forest.man` authored + parses
- [x] `disturbed.json` remap (41 deciduous, 43 mixed, 42 evergreen)
- [x] `disturbed_land_soil_lookup.csv` determination (rows added or justified)
- [x] override-path resolution verified (no fallback/error)
- [x] `winter-cancov-validation.md` (low/intermediate/high ordering)
- [x] parameterization ADR authored
- [x] tests/regression + repo QA gates

## Execution Notes

- 2026-06-26: Compatibility plan before lookup mutation:
  `disturbed_land_soil_lookup.csv` keeps its existing header and `forest` rows.
  The implementation adds `deciduous forest` and `mixed forest` rows for the
  four existing texture buckets, copying soil-hydraulic values from `forest`
  and changing only canopy/plant scalars. Existing projects and custom maps
  that still resolve to `forest` continue to use the previous evergreen
  parameterization. Regression coverage will check new management parsing,
  disturbed-map resolution, lookup rows, forest-family routing, and RUSLE
  family normalization.
- 2026-06-26: WEPP validation showed that nonzero perennial `jdplt=126`
  behaves like first-year planting for these established forest managements and
  can zero the residual canopy. The implemented managements keep `jdplt=0` and
  use growth constants plus `jdharv=286` to produce seasonal trajectories.
- 2026-06-26: Final-year single-hillslope validation showed winter mean
  `Cancov` ordering of deciduous `6.653%`, mixed `44.446%`, evergreen
  `90.000%`; see `artifacts/winter-cancov-validation.md`.
- 2026-06-26: Executed `artifacts/gdd-senescence-experiment.md` as a
  follow-up investigation using the disturbed harness slope/soil, Moran WY
  cold/high-elevation climate, and McKenzie Bridge OR warmer/lower-elevation
  climate. The GDD/`dlai` path was rejected: `jdharv=0` produced no perennial
  leaf-off, the nonzero-date gate grid produced zero correct-direction
  candidates, and some early-gate combinations emitted invalid negative
  `Cancov`. No shipped `.man` or lookup files were changed.
- 2026-06-26: Targeted QA passed:
  `wctl run-pytest tests/test_managements_module.py tests/nodb/mods/disturbed/test_lookup_contract.py tests/nodb/test_disturbed_management_overrides.py tests/nodb/mods/test_rusle_c_lookup.py tests/wepp/test_wepp_prep_managements_rap_ts.py -q`,
  `wctl run-stubtest wepppy.nodb.core.management_overrides`,
  `wctl doc-lint --path docs/work-packages/20260626_deciduous_mixed_forest_managements`,
  `wctl doc-lint --path docs/adrs/ADR-0009-deciduous-mixed-forest-managements.md`,
  `wctl doc-lint --path docs/adrs/README.md`, and
  `wctl doc-lint --path wepppy/nodb/mods/disturbed/README.md`.
