# WP03 Registry and Serializer Evidence

## Scope and Result

WP03 implements the dormant, in-memory project configuration registry and
resolver. It adds no project writer, route, queue edge, runtime flag, or run
artifact. The shipped registry has 13 real-TOML documents: one locale, two
DEMs, two delineation backends, one watershed representation, one soil source,
one land-use source, four climate sources, and one umbrella capability profile.
The implementation revision is `1bb9e49f4`.

The climate IDs retain the exact ratified underscore tokens:
`vanilla_cligen`, `prism_stochastic`, `observed_daymet`, and
`observed_gridmet`. Runtime option names retain deployed spelling such as
`[soils] ssurgo_db` and `[landuse] nlcd_db`; stable component IDs provide the
semantic vocabulary above those existing keys.

## Requirement Evidence

| Contract evidence | Implementation/test evidence | Result |
| --- | --- | --- |
| N-011, N-064 through N-067, A-003 | TOML corpus, strict schema loader, stable-ID and revision tests | Pass |
| N-030 | caller-base snapshot-independence test | Pass |
| N-058, N-059, R-003 | exact parent-chain and declared-writeover tests | Pass |
| R-029, R-030 | dormant and explicitly selected synthetic-mod test | Pass |
| N-028, N-031, N-033, N-049 | deterministic descriptor, local matrix, excluded-ID, and DEM-default tests | Pass |
| R-032, R-037 | field-addressable constraint and fixed cell-size tests | Pass |
| N-062 integration | resolved bytes validated and reparsed through WP00B | Pass |
| N-032, R-033 local contribution | all two-DEM by two-backend combinations resolve locally | Pass locally; Forest acceptance remains WP11 |

The local matrix covers exactly:

- `usgs-ned1-2024` with `topaz` and `wbt`;
- `usgs-ned13-2022` with `topaz` and `wbt`.

This does not claim that deployed datasets or services have passed the Forest
create/reopen/delineate/build gate. WP11 must accept or remove each combination
without substitution.

## Validation Record

Executed from `/home/workdir/wepppy` on 2026-08-26:

- `wctl run-pytest tests/nodb/test_project_config_registry_serializer.py --maxfail=1`: 37 passed.
- `wctl run-pytest tests/nodb/test_project_config_serialization.py --maxfail=1`: 23 passed.
- `wctl run-pytest tests/nodb --maxfail=1`: 1,740 passed, 26 skipped.
- `wctl run-stubtest wepppy.nodb.config_builder`: success, 13 modules.
- `wctl check-test-stubs`: pass.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`: pass, net delta zero.

- `wctl run-pytest tests --maxfail=1`: 6,864 passed, 63 skipped.

Documentation lint and final diff checks passed after archival; their results
are also retained in the completed ExecPlan and tracker.

## Compatibility and Recovery

Resolution deep-copies the canonical defaults map, applies only validated
component writes, serializes in memory, and returns immutable outer mappings
plus exact bytes. Invalid registries fail before exposure; invalid selections
fail before serialization. Reverting `wepppy/nodb/config_builder/` and its
tests removes the dormant feature. No project-data rollback or generated-run
cleanup is required.
