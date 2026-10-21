# Release-specific water accounting

Source: native release source `a87925df9ffe6ebb928e126395dd159d484285fa`,
artifact commit `6a6621e4db9aff1cdf6fa9cd0cb02b00e82182eb` in
`/workdir/wepp-forest-release-20261009`. This map is specific to that ASCII
PASS v3 lineage. Prior HBP writer semantics are not substituted.

## Soil and OFE boundaries

`src/watbal.for:359` adds upstream lateral flow after multiplying by the upstream
area and dividing by the receiving area. Its surface transfer uses upstream
runoff times effective length divided by receiving local length. With constant
width, multiplying both sides by local area yields matching volume. At each OFE,
QOFE is outgoing surface transfer, including inherited runoff; it is not a local
source term. Internal transfers cancel only after conversion to volume.

`src/watbal.for:956` and the corresponding `watbal_hourly.for` output block use
Q = runoff * effective length / cumulative length, and QOFE = runoff * effective
length / local length for ordinary non-contour geometry. Therefore Q times
cumulative area equals QOFE times local area. At the last OFE, use this volume
once. The contour branch writes runoff directly for both; constant-width ordinary
proof does not establish a contour or variable-width contract.

ET is Ep + Es + Er and Dp is `sep`, both OFE-local depths. Sum their local volumes,
not their depths or just the last OFE. Daily/hourly modes have different process
integration: the hourly routine distributes infiltration and computes drainage
and lateral flow over 24 steps; ET is computed once daily. The WAT file is a
daily summary even in hourly mode. `main.for` selects hourly execution from the
presence of `wepp_ui.txt`; generated WAT headers independently confirm selection.

The soil/snow screen includes reported liquid+frozen soil and snow storage
changes. It excludes the first day because pre-run stores are not printed and
explicitly does not assume unreported interception storage is zero. Rounded
WAT alone cannot certify complete physical-domain closure.

## Groundwater and PASS boundary

`contin.for:1101` accumulates Dp times every OFE’s local area into groundwater
recharge. The groundwater recurrence subtracts the previous day’s baseflow and
deep-seepage withdrawals before calculating current withdrawals. Compare matching
state times; an end-of-day post-withdrawal store is not the printed pre-withdrawal
state. The selected case starts with zero groundwater; nonzero initialization
needs its own coverage because `igwstrv` is assigned inside the OFE loop.

`wshpas.for:156` selects EVENT using internal terminal runoff >= 0.001 m; this
is not necessarily the printed cumulative-area Q. EVENT carries surface volume,
terminal lateral volume, tile volume and groundwater fields. SUBEVENT and NO EVENT
omit surface delivery. Lateral volume is terminal `sbrunf * slplen * fwidth`, with
the exact SUBEVENT threshold/nesting retained. ET is not routed in PASS. Dp is
not directly passed as runoff: it influences groundwater baseflow/deep seepage.

`wshred.for` loads the master ASCII daily arrays; `wshcqi.for:169,196` adds loaded
surface, lateral and eligible baseflow by hillslope/channel connectivity. Tile
is a distinct field and requires positive-flow testing before certifying delivery.
The controlled cases have zero tile and zero groundwater deep-seepage coefficient.

## Channel accounting and independent transport

`wshdrv.for:997–1045` forms local channel runoff and a net transmission term.
The latter may be negative; do not label it a physical infiltration loss without
tracing water-balance additions. `wshchr.for:154–202` adds lateral and top volumes
to `volint`, while constructing rate arrays `qlat` and `qin` separately.

The positive-lateral-volume branch allocates surface water through side-hillslope
hydrographs. With no side hillslopes, the calls to `chrqin` are skipped and only
subsurface/baseflow rates are added. Positive channel-local net water can then
be present in `volint` but absent from `qlat`. Native observations and controlled
network tests, not just this source reading, determine the impact.

`wshchr.for:654–657` computes published `chvol` from `volint` and endpoint-derived
storage, then resets storage to satisfy that identity. Its printed zero balance
is therefore not independent conservation evidence. Downstream rate routing uses
`q1`, whereas daily volume routing uses `tmpvol`; audit both. Read-only probes
retain all time samples including time zero, plus existing volume/state scalars.
Integrate both rectangular and trapezoidal rates independently; compare to
published volumes, local terms and storage, with native precision exposed.

## Measured hourly allocation defect

`watbal_hourly.for:520–523` stops distributing infiltration when remaining `xfin`
is within 0.00001 m. The remaining quantity is not visibly assigned to a water
store before the next hour overwrites it. The read-only per-hour probe confirms this remainder and its contribution to
soil residuals; see WPA-03 in `findings.md` and `hourly-observer-audit.json`.
