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

Full-project checks require local sites and fresh destinations. The opt-in
`test_roads_project.py` suite uses two settings **inside the test container**:
`ROADS_VALIDATION_SOURCE=/wc1/runs/cl/clogging-starch` for `inslope_bd`,
`inslope_rd`, and `outslope_rutted`; and
`ROADS_UNRUTTED_VALIDATION_SOURCE=/wc1/runs/mi/misty-eyed-divorcee` for the two
current unrutted controls. Host-only environment assignments are not automatically
forwarded by `wctl run-pytest`. With these container settings, run
`wctl run-pytest tests/roads/test_roads_project.py`; otherwise those cases skip.
Each uses the actual controller upload/prepare/run lifecycle and checks original
source and copied baseline hashes. The additive designs also support:

```bash
wctl exec weppcloud python -m tests.roads.roads_project \
  /wc1/runs/cl/clogging-starch /wc1/runs/ro/roads-validation-UNIQUE DESIGN
```

Current unrutted tests use `unrutted_project.validate_unrutted_project`, pin the
55-feature source upload, and exclude no features. The synthetic 5 m-fill control
must complete with current-result admission, native OFE role/area readback and
independent daily water reconciliation. The separate 30 m-fill control must retain
five explicit `failed_road_fill_exceeds_hillslope` failures and no current receipt.
Both prescribe fill slope 10%, buffer length 30 m and buffer slope 10%; these are
acceptance geometry inputs, not measured-site predictions or new defaults.

The historical `--verify-negative`, `--exclude-infeasible-unrutted`, and unrutted
`--verify-existing` helper paths in `roads_project.py` retain their earlier
OSUNUM6/two-failure/three-or-four-OFE assumptions for historical verification.
Do not use them to judge fresh RUPC-02 results or regenerate an earlier report.
Non-positive ordinary upstream length alone is no longer a rejection; road plus
fill exceeding hillslope length remains an explicit failure. See the
[current validation contract](../../docs/schemas/roads-validation-suite-contract.md#full-upload-unrutted-acceptance-after-rupc-02).

Never point the destination at the original site or an existing project. The
runner refuses existing destinations and verifies source and copied baseline
hashes. It changes only the scratch project. Project checks require the full
local fixture; portable profile tests do not.

Paired studies can reuse `roads_sensitivity.prepare`, `execute`, `summarize`, and
`paired_events` with an independently declared panel. Preparation uses canonical
Roads builders; geometry contrasts accept width, fill length and fill slope,
and traffic selects the existing templates. The caller must bind source and
binary identities and review the declaration before native execution. Each
capsule has an exclusive directory, input readback, complete runtime inventory,
retained failures, native tables and production segment-summary metrics. The
runner invokes the explicitly hashed installed watershed executable in hillslope
mode once, with a 300-second timeout; it retains stdout/stderr and never retries.
Before execution and summary, the helper verifies that the declared native CLI,
the discovered ancestor climate and every cached calendar date agree. Mismatches
fail explicitly; the helper does not silently repair or delete a cache.
This helper does not adopt generated-soil policies or change project defaults.
Run its deterministic safeguards with
`wctl run-pytest tests/roads/test_roads_sensitivity.py -q`.

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
