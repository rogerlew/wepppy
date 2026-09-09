# Pinned reference diagnostics

Status: pinned-reference discrepancies explained; rebuilt WBT results match
independent physical expectations. User adopted maximum-minus-outlet.

## Provenance and reproduction

Reference checkout `/workdir/usgs-pfdf`, clean revision
`2be86e5928cb5d2940f6bfb68193b00722505056` (pfdf 3.0.2).
Executed with pysheds 0.4, numpy 1.26.4, numba 0.63.1, rasterio 1.4.4,
Python 3.12 in `/tmp/staley-m3-reference-env`, a disposable venv with existing
system packages. `PYTHONPATH` explicitly selects the pinned reference checkout;
the reference is not an owned runtime dependency. No reference implementation
or tests were copied. The owned probe only constructs analytical inputs and
calls its public API.

From WEPPpy:

```bash
python -m venv --system-site-packages /tmp/staley-m3-reference-env
PYTHONPATH=/workdir/usgs-pfdf /tmp/staley-m3-reference-env/bin/python docs/work-packages/20260908_staley_m3_wbt_terrain/artifacts/reference_probe.py
```

The environment must have the listed versions; the venv creation command does
not install or pin them. Observed output is retained in `reference_probe.jsonl`.
A 5-by-9 raster contains a five-cell eastward chain at row 2, columns 2-6,
with 10 m cells, EPSG:32611, and -9999 NoData elsewhere. The third cell is the
assessment outlet; two valid downstream cells isolate it from the domain edge.
TauDEM pointer 1 means east. The final cell points into NoData. An initial
zero-terminal probe was rejected by pfdf validation, so the reported probe
uses valid TauDEM pointers throughout rather than disabling validation.

## Observations

| Five-cell raw elevations (m) | Observed relief at third cell (m) | Maximum-minus-outlet expectation (m) | Observed area (m2) |
| --- | --- | --- | --- |
| 130, 120, 100, 95, 90 | 25 | 30 | 300 |
| 110, 130, 100, 95, 90 | 35 | 30 | 300 |
| 130, 90, 100, 95, 90 | 5 | 30 | 300 |

The descending case also disagrees with both highest-source and max-minus-min
semantics. Across these three diagnostic outlets the absolute H discrepancies
against maximum-minus-outlet are median 5 m, maximum 25 m. Area discrepancies
are zero. Absolute T discrepancies are median 0.2886751346, maximum
1.4433756730, using sqrt(300). These initial M1 observations were analytical-reference comparisons; the
final rebuilt WBT comparison is documented below.

The full descending relief sequence is 0, 20, 25, 30, 10119 m.
The last value is consistent with contamination by the -9999 sentinel.
The second-cell value corresponds to its outgoing drop rather than the
source-to-second-cell drop. These observations indicate weight-location and
boundary defects relative to the documented physical interpretations;
they are not proof of the intended calibration algorithm. No attempt was
made to reproduce the erroneous behavior in owned code.

## Primary evidence and unresolved interpretation

The locally supplied manuscript SHA-256 is
`72de34d27231acd14cc0ba8daf431e9121464132072447aef6ff658b687e660b`.
Section 5.2 describes upslope relief divided by area without a square root;
Table 4 names ruggedness without defining raw-elevation extrema or conditioning
semantics. All nine M3 coefficients and three intercepts match the current
module specification after independent Table 4 readback.

The [USGS model guide](https://ghsc.code-pages.usgs.gov/lhp/pfdf/guide/models/s17.html)
supports H/sqrt(A). The
[USGS watershed API](https://ghsc.code-pages.usgs.gov/users/jking/pfdf/api/watershed.html)
uses inconsistent nearest/highest ridge descriptions while allowing raw DEMs.
Neither source resolves the three competing raw-elevation definitions.
Direct model-guide retrieval returned 403; indexed primary-source content and
local reference documentation were available. No unsupported parity claim is
made. This prompted the user to adopt maximum-minus-outlet before M2.

## Rebuilt owned command comparison

The final binary was run on the exact same five-cell grids used by pfdf,
converting only WBT east=2 to TauDEM east=1. Both preserved the same masks,
measurement DEM and third-cell assessment outlet. See
[generated comparison](reference_built_comparison.json) for complete sequences,
binary identity, reference module and package versions. The reproducible
harness is `/workdir/weppcloud-wbt/tools/staley_m3_reference_compare.py`.

WBT returns 30 m and 300 m2 at all three assessment outlets, matching the
adopted definition, including the raw internal maximum and conditioned pit.
The pinned reference returns 25, 35 and 5 m with the same correct areas.
The absolute H discrepancies remain median 5 m, maximum 25 m; T discrepancies
remain median 0.2886751346, maximum 1.4433756730. Area discrepancy is zero.

The descending-chain reference sequence is consistent with omitting the first
edge drop and including the assessment cell's outgoing drop. The pit case
also indicates that rising-edge handling does not preserve signed telescoping
differences. The final outgoing-to-NoData cell is sentinel-contaminated.
These observed patterns explain why scalar tolerances cannot establish parity;
no GPL recurrence was translated into owned code. The owned algorithm's
independent extrema/count verification is the correctness anchor.

All 24 study outlet pairs additionally passed independent catchment cell-count
and raw-maximum-minus-outlet checks using the owned Watershed command's saved
masks. Correctness review independently rechecked the arrays and all 864 M3
scenarios. The reference discrepancies therefore do not become unexamined
terrain error in the resolution study. Original Staley calibration
preprocessing equivalence remains unproven and is not a claimed deliverable.
