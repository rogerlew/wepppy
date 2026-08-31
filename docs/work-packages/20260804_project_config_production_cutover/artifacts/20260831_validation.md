# WP12 pre-merge validation

**Date**: 2026-08-31

**Validated runtime candidate**: `85eb7d309` plus the bounded public-stub and
generated RQ evidence corrections recorded below. The final documentation
checkpoint will record the resulting exact feature revision before merge.

## Automated gates

- `wctl run-pytest tests --maxfail=1`: 7,280 passed, 63 skipped, 0 failed in
  12 minutes 42 seconds on the successful complete run.
- `wctl run-npm lint`: passed.
- `wctl run-npm test`: 108 suites and 833 tests passed.
- `wctl check-test-stubs`: passed after the final stub correction.
- Scoped `wctl run-stubtest` passed for ESDAC soil diagnostics, RQ creation
  idempotency, Builder registry/resolver/schema/snapshot, landuse, project
  capability authority, project config reader/snapshot/update, and their public
  runtime surfaces.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref
  origin/master`: passed; net unsuppressed broad-catch delta is -1 across 49
  changed Python files.
- `.venv/bin/vulture`: passed with no output.
- `wctl check-rq-graph`: passed after regenerating a source-line-only drift for
  `upload_cli_rq`; the graph remains 144 edges and no dependency changed.
- `git diff --check`: passed after removal of six historical review-artifact
  EOF blank lines and WP12 formatting corrections.
- `wctl doc-lint --path
  docs/work-packages/20260804_project_config_production_cutover`: 4 files, 0
  errors, 0 warnings before the review artifacts were added; rerun is required
  at the final documentation checkpoint.
- `wctl doc-lint --path PROJECT_TRACKER.md`: 1 file, 0 errors, 0 warnings.
- `python3 tools/code_quality_observability.py --base-ref origin/master`:
  completed in observe-only mode and refreshed the tracked reports.

## Failure dispositions

The first complete Python attempt stopped after 2,886 passes and 41 skips at
`test_unrelated_same_size_rewrite_is_preserved_during_finalization` because its
fixture could not construct a same-size rewrite. The exact test passed on an
immediate isolated rerun. The second complete suite passed through that test
and finished green. This is the previously observed probabilistic fixture-
construction miss; it does not indicate a product assertion failure and no
production or test change is justified in WP12.

`wctl check-test-isolation` was stopped after its first worker ran for more than
four minutes without progress output. With no randomization plugin installed,
the tool defaults to five complete `tests` runs plus per-file checks rather than
the intended shuffled isolation probe. The canonical full suite passed, and no
changed-code isolation failure was reported before termination. This is a tool
execution disposition, not a green isolation claim.

The first scoped stub sequence found one real defect:
`wepppy.nodb.project_config_snapshot.__all__` exported
`resolve_preset_locale_projection` while the `.pyi` omitted it. WP12 added the
exact runtime signature to the stub and reran the snapshot/update comparisons,
stub completeness, and 54 direct preset/capability tests successfully. This is
an additive type-surface correction with no runtime behavior change.

The first RQ graph check found only the changed source line of the existing
`upload_cli_rq` enqueue call (`145` to `182`). Canonical regeneration updated
the static JSON and managed catalog line number; the follow-up graph check
passed with the same 144 edges.

## Manual and deployed acceptance retained

WP12 retains the exact-host Forest evidence from WP11 and WP12B-D, including
five Builder locales, real landuse/soil/climate builds, Legacy/2015/GHCN station
database isolation, legacy project reopening, capability refresh and rollback
reader compatibility, table accessibility, and default-BLC Multiple-OFE
execution. These are deployed acceptance results, not substitutes for the
automated gates above.

