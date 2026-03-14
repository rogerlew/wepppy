# POLARIS Phase-1 Validation Summary

## Scope

Validation target for phase-1 contract:
- Retrieval + alignment only.
- Manual enqueue/trigger path retained.
- GeoTIFF output only.

## Commands and Results

1. Focused test suite

```bash
wctl run-pytest tests/nodb/mods/polaris/test_polaris.py tests/microservices/test_rq_engine_polaris_routes.py -q
```

Result:
- `7 passed`
- Added direct `Polaris.acquire_and_align()` skip/force-refresh coverage.

2. Changed-file broad exception enforcement

```bash
python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
```

Result:
- `PASS`

3. RQ dependency graph drift check

```bash
wctl check-rq-graph
```

Result:
- `RQ dependency graph artifacts are up to date`

4. Docs lint (work package + tracker)

```bash
wctl doc-lint --path docs/work-packages/20260313_polaris_nodb_runs_client
wctl doc-lint --path PROJECT_TRACKER.md
```

Result:
- Clean (no errors/warnings)

5. Full-suite sanity

```bash
wctl run-pytest tests --maxfail=1
```

Result:
- `2321 passed, 34 skipped`
- During closeout, two route-freeze drifts were surfaced and resolved:
  - endpoint inventory freeze (`endpoint_inventory_freeze_20260208.md`)
  - route contract checklist freeze (`route_contract_checklist_20260208.md`)

## Real-Run Integration Validation

Run:
- `runid`: `insightful-peacock`
- Working directory: `/wc1/runs/in/insightful-peacock`

Execution:
- Created `polaris.nodb` for the run (did not previously exist).
- Ran acquisition/alignment for `sand_mean_0_5` with `force_refresh=true`.

Observed outputs:
- `/wc1/runs/in/insightful-peacock/polaris.nodb`
- `/wc1/runs/in/insightful-peacock/polaris/sand_mean_0_5.tif`
- `/wc1/runs/in/insightful-peacock/polaris/manifest.json`
- `/wc1/runs/in/insightful-peacock/polaris/README.md`

Grid parity check against run DEM (`/wc1/runs/in/insightful-peacock/dem/dem.tif`):
- CRS equal: `true`
- Transform equal: `true`
- Shape equal: `true` (`369 x 381`)

Acquisition summary:
- `layers_requested=1`
- `layers_written=1`
- `layers_skipped=0`

## Remaining Gaps

- None for phase-1 retrieval/alignment scope.
