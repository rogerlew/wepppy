# M3 Terrain Contract and Resolution Findings


Pending production amendment (2026-09-11): [ADR-0066](../../../../../docs/adrs/ADR-0066-staley-valid-support.md)
and [model selection](model_selection.md) record scalar valid-support estimates,
coverage artifacts and the initial M3 NED13/2022 10 m source requirement.
Existing local tool outputs remain unchanged; scientific composition follows
its own checkpoint after UI/task wiring.

## Accepted engineering definition

The user adopted the following contract on 2026-09-08 America/Los_Angeles;
[ADR-0052](../../../../../docs/adrs/ADR-0052-staley-m3-upstream-terrain.md)
records provenance and rationale.

```text
H(o) = maximum raw elevation among all upstream cells including o - raw elevation at o
A(o) = upstream cell count including o * projected cell area
T(o) = H(o) / sqrt(A(o))
```

H is in meters, A in m2 and T is dimensionless. Use the existing conditioned
WBT D8 routing and an explicitly identified raw elevation measurement surface.
Do not use WEPPcloud `wbt/relief.tif` directly as H: it is a conditioned DEM.
Internal raw elevation maxima are included, and depressions above the outlet
do not replace the outlet elevation with catchment minimum. Highest-source
and catchment max-minus-min alternatives were rejected for those reasons.

## Owned implementation and input contract

The registered Rust `D8UpstreamRelief` command and both WBT Python bindings
calculate H/A with an O(N) upstream traversal. Required flags are `--dem`,
`--d8_pntr`, `--output`, `--area`, and `--elevation_units=m`; optional
`--coverage` writes a potential-truncation flag. The durable CLI/algorithm guide
is `/workdir/weppcloud-wbt/docs/d8_upstream_relief.md`.

The initial interface accepts aligned, single-band, north-up pixel-area
GeoTIFFs in WGS84 UTM meter CRSs. It rejects inconsistent units, unsupported
CRSs, mismatched NoData masks, nonfinite valid data, invalid pointers and
cycles. WBT encoding is NE=1,E=2,SE=4,S=8,SW=16,W=32,NW=64,N=128, zero
terminal. Routing into NoData/exterior terminates within the available domain.

H/A are Float64; coverage is UInt8, propagating potential edge/NoData contact
downstream. Flagged quantities must not be presented as proven complete
catchments. Outputs must be new paths; each is published without replacing
an existing file, using a private staging directory and hard link. A later
failure can leave an incomplete published set. Stable caller-controlled input
files and parents and a filesystem supporting hard links are required.
This package adds no production NoDb, UI, RQ, deployment or binary vendoring.

## Correctness and external reference

The final rebuilt command and both wrappers generate independent analytical
expectations. At the end of a 130,120,100 m chain of 10 m cells, H=30 m and
A=300 m2. On raw 130,90,100 m with identical routing, outlet H remains 30 m.
Study catchment masks independently reproduce generated maxima and counts.

Pinned pfdf 3.0.2/pysheds 0.4 returns 25 rather than 30 m in a monotonic
five-cell probe at its third cell, and exhibits an outgoing-to-NoData anomaly.
The registered owned implementation intentionally does not reproduce these
reference defects. See [comparison evidence](../../../../../docs/work-packages/20260908_staley_m3_wbt_terrain/artifacts/reference_parity.md).
No GPL source/tests were copied or translated. The paper's prose and reference
documentation do not settle original calibration preprocessing; this engineering
contract does not claim to reconstruct it exactly.

## Resolution recommendation

Require genuine 10 m terrain for initial M3 support. Do not accept 30 m as a
general substitute, and do not infer a universal large-catchment exemption.
This is a recommendation for future production integration, not implemented
availability enforcement. The [decision report](../../../../../docs/work-packages/20260908_staley_m3_wbt_terrain/artifacts/resolution_decision.md)
contains reproducible data, plot, pairing limitations and criteria sensitivity.

The panel covers three supplied sites and 12 terminal/nested outlets, each
compared under controlled aggregation/preprocessing and native workflows:
24 pairs, 864 diagnostic M3 scenarios. Controlled differences reach 10.598
probability percentage points and 12.479% inverse-threshold change. Both
comparison sets fail the predeclared 5-point/10% screen at two of 12 outlets.
Main outlets agree within 0.459 points, which would conceal small-catchment
failures if considered alone. Some nearby snapped cells delineate substantially
different catchments; small coordinate offsets do not prove equivalence.

Fixed F/S and nonsaturated probabilities isolate terrain sensitivity, not
prediction skill or production SSURGO readiness. The user-labeled AZ terminal
is about 23 km2 and lies outside the paper's reported 0.02-8 km2 range; its
label is retained as provenance, not verified geographic identity. The limited
panel does not establish CONUS-wide validity. Upsampling 30 m does not restore
10 m information. Broader same-channel small-catchment evidence is needed to
revisit 30 m acceptance.
