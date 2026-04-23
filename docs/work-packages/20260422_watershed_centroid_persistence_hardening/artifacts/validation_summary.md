# Validation Summary

## Targeted Regression

Command:

```bash
wctl run-pytest tests/nodb/test_watershed_runtime_contract.py tests/nodb/test_base_boundary_characterization.py tests/rq/test_project_rq_mutation_guards.py tests/nodb/test_climate_station_catalog_service.py tests/nodb/test_climate_facade_collaborators.py tests/nodb/mods/disturbed/test_sbs_validation.py::TestColorTablePreservation::test_get_sbs_preserves_color_table --maxfail=1
```

Result: `43 passed`

## Full Suite Gate

Command:

```bash
wctl run-pytest tests --maxfail=1
```

Result: failed on unrelated existing worktree failure:

- `tests/nodb/mods/geneva/test_geneva_wp09_end_to_end.py::test_wp09_watershed_warning_thresholds_propagate_to_results_query_report[30000000.0-warning]`
- Error: `KeyError: 'severity'`

## Notes

- Package-scoped centroid and stale-write hardening paths are covered by targeted passing tests.
- Full-suite blocker is outside this package's touched files.
