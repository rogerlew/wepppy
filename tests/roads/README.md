# Roads validation suite

This suite uses scientific inputs extracted from `clogging-starch` to compare
native Roads profile detachment across clay, loam, sand and silt; gravel/paved;
high/low/no traffic; seven OFE arrangements; and three actual segment geometries.
The 504 combinations plus 12 one-factor controls use the same 2000–2015 climate.
The canonical contract is [roads-validation-suite-contract.md](../../docs/schemas/roads-validation-suite-contract.md).

## Execute and inspect

Run through the development container. Choose a new basetemp to retain evidence:

```bash
wctl run-pytest tests/roads/test_roads_matrix.py --basetemp=/tmp/roads-validation -q
wctl exec weppcloud python -m tests.roads.roads_analysis /tmp/roads-validation/roads_matrix0
wctl run-pytest tests/roads/test_roads_contracts.py -q
```

The analyzer requires all 516 successful cases and verifies generated input,
output and template hashes. Partial runs cannot produce a current report.
Native PASS/WAT readers and the production segment summary calculate the metrics;
there is no second Python model. The committed report and machine-readable
summary are publication artifacts; raw inputs/outputs remain under basetemp.

Full-project checks require the local site and fresh destinations. They are also
available as opt-in pytest cases via `ROADS_VALIDATION_SOURCE=/wc1/runs/cl/clogging-starch`
and `wctl run-pytest tests/roads/test_roads_project.py`; default suite runs skip them. Each uses the
actual controller upload/prepare/run lifecycle, explicit feature design values,
and independent daily area/water reconciliation. For each of `inslope_bd`,
`inslope_rd`, `outslope_rutted`, and `outslope_unrutted`, run:

```bash
wctl exec weppcloud python -m tests.roads.roads_project \
  /wc1/runs/cl/clogging-starch /wc1/runs/ro/roads-validation-UNIQUE DESIGN
```

The full upload assigned to unrutted design is an expected negative geometry
control at this site (two non-positive upstream OFEs). Verify that retained
failure with `--verify-negative`. The separately reviewed positive control uses
`--exclude-infeasible-unrutted`, excluding exactly source OSUNUM6 with a pinned
feature hash. Its 54-feature input is not a full-upload design comparison.
`--verify-existing` rechecks a completed run's artifacts and recorded source
hashes without repeating the model execution.

Never point the destination at the original site or an existing project. The
runner refuses existing destinations and verifies source and copied baseline
hashes. It changes only the scratch project. Project checks require the full
local fixture; portable profile tests do not.

## Interpret results

Detachment is native mean annual full-profile detachment, including non-road
OFEs in mixed profiles. Dividing by WAT full-profile area does not produce a
road-prism-only erosion rate. Sediment export is not watershed outlet yield.
Differences between arrangements include different modeled footprints.

The shortest road segment is only 8.6 mm and is a numerical stress case. Requested
and emitted geometry, including unrutted parity transformations and bounds, are
retained. Fill/buffer/landuse dimensions are prescribed experimental controls.
The climate header advertises 100 years, but its rows contain only 16; the suite
uses actual dates. The pinned binary matches the site's `wepp_260409` build.
Scientific ranking anomalies remain visible; monotonic response is not a test.

## Refresh fixtures and publication

`extract_fixture.py SOURCE` explicitly refreshes the small scientific fixture
and its provenance; review the change and rerun the matrix. Do not copy serialized
project state into the repository. Report refresh must include relevant source,
binary and native-library identities, actual completed matrix evidence, project
checks and scientific review. Updating hashes alone does not establish freshness.

The report is vendored through the scoped `wepppy-roads` Usersum vendor. Use the
existing vendor sync API with that vendor alone, then build the index with
`--skip-vendor-sync`; the default CLI syncs unrelated vendors too. The canonical
report and vendor copy must be byte-identical. See the suite contract for the
publication path and required user-visible link.

Publish only after complete analysis and scientific review:

```bash
wctl exec weppcloud python -m tests.roads.roads_report MATRIX_ROOT \
  BARE_PROJECT ROCKED_PROJECT RUTTED_PROJECT UNRUTTED_POSITIVE_PROJECT \
  --unrutted-negative UNRUTTED_NEGATIVE_PROJECT
```

`analysis_context.md` contains the reviewed interpretation. Generated tables,
case summaries and provenance must be refreshed together; then perform scoped
Usersum sync and run `test_roads_publication.py`.
