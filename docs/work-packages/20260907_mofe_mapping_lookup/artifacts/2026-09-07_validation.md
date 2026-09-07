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
- Observe-only code quality completed; radon unavailable, so no Python complexity metric. Its changed-file report uses committed changes and did not include this uncommitted production edit. Generated root report files were restored to avoid unrelated churn. The production delta is 17 added / 4 removed lines, with no new branch.
- Spelling preview: new/changed package and domain docs clean; root tracker has pre-existing differences outside this change.
- Full suite: running; final outcome follows.

## Operational follow-up

Deployment and recovery of aliquot-shoji are outside this repository package. After rollout, rebuild landuse from baseline and confirm all resulting management IDs belong to the effective map. Observe recurrence on the next C3S MOFE rebuild; investigate semantic-class selection if the signature recurs.
