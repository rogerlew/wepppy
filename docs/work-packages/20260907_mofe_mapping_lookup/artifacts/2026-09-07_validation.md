# MOFE mapping lookup validation

**Date**: 2026-09-07 UTC  
**Contract ancestor**: 38789cb4c

## Regression and generated artifacts

Before production edit, the new effective-map test passed for disturbed and failed for C3S with KeyError: 106. After correction, all 18 remap tests passed. The generated-artifact assertions then also passed (18 tests): real map loading, real get_management_summary, real _write_mofe_management_file_task synthesis, real Management parsing/multi-year expansion, and temporary wepp/runs/p1.man readback. Each of 12 burned segments retains expected canopy/interrill/rill cover from its resolved source summary.

Maps exercised: disturbed, c3s-disturbed, and a run-scoped custom C3S map with nonnumeric prefixed keys. The custom-map selection uses actual Landuse.get_mapping_dict and effective-map path resolution.

The raster/SBS grids, NoDb locks, and build_managements scheduling are isolated with fixtures; these tests are not a complete live landuse or WEPP simulation replay. No safety, persistence, filesystem, or process boundary implementation changed. No production data was modified.

## Commands and results

- Baseline: wctl run-pytest tests/nodb/mods/disturbed/test_landuse_remap.py --maxfail=1: 7 passed.
- Regression before fix: wctl run-pytest tests/nodb/mods/disturbed/test_landuse_remap.py -k mofe_effective --maxfail=1: 1 passed, 1 failed (C3S key 106).
- Final focused: wctl run-pytest tests/nodb/mods/disturbed/test_landuse_remap.py --maxfail=1: 18 passed.
- Related suite: wctl run-pytest tests/nodb/mods/disturbed tests/nodb/test_landuse_mofe_disturbed_scalar_lookup.py tests/nodb/test_landuse_mofe_process_pool.py tests/nodb/test_landuse_mofe_value_types.py --maxfail=1: 110 passed, 20 skipped (live/optional raster tests).
- python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master: PASS; broad catch delta zero.
- Documentation lint: package, canonical contract, and disturbed README passed.
- Observe-only code quality rerun after implementation commit with /tmp outputs: production source lines 2338 to 2351 (+13); maximum function length unchanged at 378. Existing controller remains in the red size band. Rationale: explicit semantic lookup expressions replace compact hardcoded IDs without adding branches or unrelated refactoring. Test source lines 322 to 454, green band. Radon unavailable, so Python complexity is unmeasured. Earlier generated root reports were restored to avoid unrelated churn.
- Spelling preview: new/changed package and domain docs clean; root tracker has pre-existing differences outside this change.
- Full suite: wctl run-pytest tests --maxfail=1: 7662 passed, 72 skipped, 3105 warnings in 780.99 seconds; exit 0 (2026-09-07 19:45 UTC).

## Operational follow-up

Deployment and recovery of aliquot-shoji are outside this repository package. After rollout, rebuild landuse from baseline and confirm all resulting management IDs belong to the effective map. Observe recurrence on the next C3S MOFE rebuild; investigate semantic-class selection if the signature recurs.
