# Tracker

## Progress

- 2026-10-16 17:57 UTC: Operator approved explicit NoScaling for new projects.
- Contract and ADR prepared; both independent reviews passed after disposition
  of state-matrix and evidence-precision findings. See the review artifact.
- Operator authorized the checkpoint commit; ancestor `88c8c9fdc` committed
  before implementation edits. Constructor fix implemented.
- Regression first reproduced the unset default; after the fix, all 287 focused
  tests passed across climate catalog, EDDE builder, scaling service and Pure
  control rendering.
- Final independent review passed. Follow-up 19 new-project cases passed with
  four added legacy-setting cases and Redis disabled for disk reload; 291
  distinct focused cases passed across both runs.

## Decision log

Preserve configuration resolution, then replace only an unset constructor mode
with NoScaling. Do not change existing stored None or getter behavior.

## Validation

Verified: real constructor persistence/reload; absent/empty/None/null settings;
all five configured modes; factor/map and explicit-mode precedence; malformed
mode/factor failures; exactly one checked default radio; fixed-seed precipitation
equality for None versus NoScaling. Existing saved state is not migrated.

Command: `wctl run-pytest tests/nodb/test_climate_catalog.py
tests/nodb/test_climate_edde_build.py tests/nodb/test_climate_scaling_service.py
tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`.

Broad suite restarted after implementation because the prior process had loaded
the old constructor. Current command: `wctl run-pytest tests --maxfail=1`;
log `/tmp/climate-default-full.log`. Finished with 10,734 passed, 126 skipped,
and one failure in `test_real_file_sql_http_browser_chain`: its Playwright
Chromium executable was missing. This is not a passing broad gate. Final review
passed; constructor and rendered-control checks are separate, not a browser
integration claim. No production deployment or production job retry performed.
