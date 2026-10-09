# PRISM downstream alignment results

2026-10-09 UTC, forest, checkpoint `18076eaa9` plus the working-tree implementation.

## Outcome

Historic PRISM mode 16 now passes OpenET climate validation and AgFields observed
readiness. Production changes are the two allowlist entries. No year, sampling,
ET, crop parameterization, feature access or output-schema rules changed.

## Native AgFields evidence

The source run is `/wc1/runs/ch/chemotherapeutic-scope`; probes write only under
`/wc1/prism-downstream-alignment-20261008`. Container identity is UID 1000/GID 993.
Three hillslopes (Topaz 183/202/381, WEPP 38/42/86) were exercised for both archived
spatial methods. The production subfield writer, crop rotation synthesis,
`run_hillslope` and `wepp_260430_hill` binary ran without mocks. Fixture routing
substituted the read-only source Climate/Landuse controllers and isolated paths.

All six runs have 1,096 daily water-balance rows for 2019–2021, including February
29, 2020. Generated run files resolve `../../runs/p<parent>.cli`; SHA-256 matches
the archived prepared parent file. Daily model precipitation matches that CLI
within the existing 0.051 mm output precision tolerance. `agfields-native.json`
retains parent hashes and exact references.

Six actual readiness/schedule probes accept PRISM and Crop2019/Crop2020/Crop2021,
reject a missing Crop2020 column, and distinguish absent parent inputs from
available parent files. The isolated probes deliberately lack watershed
abstraction: its readiness flag remains false. This proves independent gates,
not completion of an entire AgFields browser/setup/watershed workflow.

An initial management-synthesis fixture (`canola_spring_mt.man`) failed the native
WEPP plant-height guard for an existing zero-height crop entry. The final probes
use the existing one-year `Agriculture/corn-no till.man`, repeated three times,
without modifying management parameters. This is fixture selection, not a PRISM
failure or a general assertion about crop-library quality.

## OpenET evidence

The actual production `OpenET_TS.acquire_timeseries` accepted PRISM and attempted
three hillslopes for both configured Climate Engine variables over 2019–2021.
All six returned HTTP 401 with the configured credential. Analysis correctly
reported no cached parquet inputs. `climate-engine-probe.json` records this
external blocker without credentials. The separate `/home/validate_key` probe
also returns HTTP401 with `Invalid API token` (see
`climate-engine-key-validation.json`). The client's raw Authorization header
matches the [official Python examples](https://www.climateengine.org/apis/python-scripts/).
A valid [Climate Engine key](https://climateengine.org/apis/requesting-an-authorization-key-token/)
is required. Production acquisition is not validated.

A separate direct OpenET API probe used the operator-provided `~/openet.key`:
Ensemble and eeMETRIC, version 2.1, monthly ET, polygon mean, millimeters. All six
requests returned HTTP 200 and each returned all 36 months, with no null ET.
Raw public requests/responses are retained in `direct-openet-*.json`.

All 216 observations join by Topaz ID/year/month to 36 real WEPP months per
hillslope for each spatial method: 432 matched comparison rows in
`monthly-alignment.csv`. February 2020 has 29 model days. WEPP ET is the sum of
Ep, Es and Er; satellite missingness is never converted to zero. Coverage and
join counts are in `openet-coverage.json` and `alignment.json`.

This establishes calendar compatibility, not model skill or equivalence between
the direct API's polygon mean and Climate Engine's configured median/products.
The sample is bounded to three existing polygons, including one very small
hillslope; it does not establish regional satellite quality or availability for
all PRISM years. No production provider fallback was introduced.

## Validation and remaining work

- Initial regression reproduced the prior rejection: mode 16 ValueError.
- Focused OpenET/AgFields/backend/routes/access tests: 182 passed.
- Updated real-template parent-reference tests: 3 passed.
- Documentation lint and changed-file broad-exception gate: pass. The allowlist's
  two existing OpenET handler line references moved by one line; handlers did not change.
- Full `wctl run-pytest tests --maxfail=1`: **10,491 passed, 126 skipped**,
  5,482 warnings, 2,676.88 seconds (44m36s). This covers the complete current
  working tree, including the preceding historic PRISM integration.
- Source integrity: all 106 checked current parent CLI/model files match the saved
  nearest-cell archive; mode16/spatial2 and 2019–2021 remain ready.
- Forest `rq-engine`, `rq-worker` and `rq-worker-batch` were restarted after all
  11 workers were confirmed idle. RQ health is OK, all 11 workers returned idle,
  and worker-side PRISM validation returns 2019–2021. Web was not restarted
  during its active test process. No production hosts were changed.
- To finish the production OpenET acquisition check, supply a valid Climate Engine
  credential and repeat the isolated `forest_alignment.py openet` probe. Direct
  OpenET data do not count as that missing acceptance evidence.

Operator disposition: the Climate Engine token is known to be expired. The
operator authorized commit/push with renewal and production acquisition recheck
deferred; the HTTP401 evidence is not a successful acquisition result.
