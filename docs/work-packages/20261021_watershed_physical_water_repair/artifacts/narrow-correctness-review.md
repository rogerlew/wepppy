# Narrow correction review

Independent correctness/scientific review, 2026-10-21. Scope: changes to native
`src/contin.for`, `src/watbal_hourly.for`, `src/chrqin.for`, their portable tests,
and the retained isolated hillslope replay receipts. Native paths are relative
to `/workdir/wepp-forest-release-20261009`, baseline `6a6621e4`.
The external WPA-01 channel experiment is not approved by this review.

Final narrow-code disposition: **no open medium/high correctness finding** in
the three reviewed source corrections after the revisions below. The independent
targeted run passes 118 tests; six known channel-local cases are deliberately
excluded. This approves the narrow code, not complete routing, full-period
acceptance of a later binary, or release readiness.

## Findings and disposition

### NC-01 — High: feasible negative withdrawal rejected

The initial allocation repair stopped after its proportional pass and declared
any remaining withdrawal impossible. Earlier layers can retain available water
when a later layer cannot supply the entire remainder. The native allocation
probe reproduced this with three layers containing 0.01 m each:

| Demand | Tillage depth | Initial available | Remaining demand at failure | Remaining liquid |
| ---: | ---: | ---: | ---: | ---: |
| -0.025 m | 0.3 m | 0.030 m | -0.00111111067 m | 0.00611111056 m |
| -0.020 m | 1.0 m | 0.030 m | -0.00619999878 m | 0.0161999986 m |

Source boundary: `src/watbal_hourly.for:494` allocation and subsequent
`HOURLY_WATER_UNMET` check. The initial small-negative tests all used uniform
wet profiles with demand far below available storage, so they did not exercise
this failure. The original 44-year replay success does not establish correctness
for these feasible input states.

**Disposition: closed.** The first variant is rejected. A bounded second pass now draws
remaining demand top-down from still-available liquid. That preserves positive
allocation and successful first-pass placement and is a defensible minimal
redistribution policy. Large-demand tests were added; NC-02's final revision
also passes. Retain the actual two-pass policy in the native contract and ADR.

### NC-02 — Medium: exact-capacity withdrawal fails on subtraction roundoff

The binary32 second-pass variant falsely rejects three layers of 0.01 m with
withdrawal 0.03 m and tillage depth 1.0 m. All stores become zero, but native
subtractions leave `xfin=-4.65661287e-10 m`. The independent rerun produced
97 passed, one failed, six deliberately deselected channel tests; the failure
was `test_profile_wide_withdrawal_uses_remaining_layers[1.0--0.03]`.

**Required correction:** distinguish original inventory feasibility from
allocation arithmetic. Sum the original binary32 liquid stores in binary64,
check whether demand exceeds that inventory, and keep working stores and
remaining demand in binary64 through the allocation before final binary32
writes. Casting after every subtraction can reintroduce the shortage. Exact
inventory exhaustion may explicitly empty all eligible stores; that is a
physical equality condition. Any numerical residual allowance must derive from
operation count and floating-point representation, never from the observed
failure magnitude. Positive allocation behavior should remain unchanged.

**Disposition: closed.** The final code checks original binary64 inventory,
handles exact exhaustion directly, keeps working stores/remainder in binary64
through both bounded passes, and casts final stores once. The exact-capacity
regression passes. True insufficient inventory still fails explicitly. No
residual tolerance or silent reduction of a physical flux was introduced.
Independent heterogeneous-profile evidence appears below.

### NC-03 — Medium: new flat-source division lacks duration validation

`src/chrqin.for:119` divides positive source volume by duration without checking
that duration is finite, positive and within the daily routing horizon.
The native CHRQIN harness with volume 100,000 m³ and peak 1 m³/s reproduces:

| Duration | Result |
| ---: | --- |
| 0 s | Nonfinite rate array and NaN integrated volume |
| -1 s | Successful return with zero delivered volume |
| 86,400 s | 99,999.99936 m³, consistent with binary32 output precision |
| 90,000 s | Successful return with 96,000.004224 m³; support is truncated |

The harness lacks floating-point traps; the production makefile traps division
by zero, so the zero-duration path would terminate at arithmetic instead of
emitting a useful source-contract failure. `src/wshred.for:153` passes duration
through without validation. `src/wshpas.for:181` guards a local `dursf` for a
different computation but serializes raw `dur` at line 229. Valid positive
duration is therefore a precondition that the consuming routine must enforce.

**Required correction:** reject invalid flat-source duration explicitly before
division, with context and native error behavior consistent with the existing
`MIXRETURN` validation in `src/mixpass.for`. Add zero, negative, nonfinite and
beyond-horizon duration controls. Do not invent a fallback duration or extend
event support.

**Disposition: closed.** Native CHRQIN now rejects nonfinite duration and duration
outside (0,86400] before arithmetic. All five invalid-input controls pass. An
intermediate `dtchr*ntchr` upper bound was rejected because native binary32 grid
rounding can put that product below 86,400 s (161 steps gives 86,399.9921875 s).
The final bound is the physical day, consistent with existing MIXRETURN behavior.

### NC-04 — Medium: accumulated flat-overlap cancellation on fine grids

Single-precision `ti` and `tl=ti-dtchr` lose interval-width precision repeatedly
on allowed nondivisor grids. The production CHRQIN harness with V=86,400 m³,
T=86,400 s and 1,413 steps delivered 86,401.694674 m³, exceeding the declared
2e-6 relative source tolerance by almost a factor of ten. At 1,384 steps the
excess was 1.662499 m³. The original 600-second controls did not expose it.

**Disposition: closed.** Flat rate and interval endpoints now use binary64,
with endpoints formed independently as `(it-1)*dt` and `it*dt`, and a single
cast when adding the cell mean to qin. Tests at 1,384, 1,413 and 1,435 steps now
pass the existing bound. The implementation follows the existing MIXRETURN
overlap pattern without relaxing tolerances or extending physical support.

## Changes with no additional major finding

Groundwater initialization uses the sum of local OFE areas, resets recharge and
previous withdrawals once at first day/first OFE, and retains the established
daily recurrence. The source change avoids terminal-OFE area and ordinary
year-boundary reset. Portable tests exercise first-day layouts, recharge,
deep seepage, a year boundary and simulated successive hillslope initialization.
The six retained 44-year groundwater receipts show successful completion and
unchanged WAT payloads.

For finite positive within-day duration, the flat branch implements the reviewed
V/T interval-overlap policy. The aligned, fractional and substep controls cover
both source approximation modes and initial/continuing boundaries. Exponential
code is unchanged. Its interval means still require a verified conversion at
the consuming solver boundary; this review does not approve point-rate routing
or physical channel storage merely because source-cell sums pass.

## Evidence and residual coverage

The review ran production blocks through existing compiled native harnesses,
not a Python reimplementation. Initial independent reproductions are retained
under `/tmp/physical-water-review-pznxo1_p` and
`/tmp/physical-source-review-sjhy74rw`; the permanent regression cases belong in
`tests/test_physical_water.py`. The rerun command was:

    PATH=/usr/bin:/bin /workdir/wepppy/.venv/bin/python -m pytest -q tests/test_component_reconstruction.py tests/test_physical_water.py -k 'not channel_local'

Final independent result: **118 passed, six deselected**. The deselected cases
exercise the unpromoted channel-local repair and are not counted as passing.
Reviewed source SHA256 values:

| Source | SHA256 |
| --- | --- |
| `src/contin.for` | `bf5b21b8e50800aad1d91c8caee550776e7b5e5b36a42260347874f73a02414f` |
| `src/watbal_hourly.for` | `c828a9b714347f0aa6f8e62509328a7c4dfe3b629d3c30029e300a7a8514bb32` |
| `src/chrqin.for` | `1a987474cca1e1e9f0a2973fe6eeeb9cb75036aa11abb27baba672abbf0739d5` |

An additional native probe evaluated 3,473 feasible heterogeneous profiles from
4,000 deterministic candidates (`numpy.default_rng(101)`). Profiles used one
through ten layers, mixtures of dry layers and 1e-8 through 1e-1 m liquid,
withdrawal fractions 0.1/0.5/0.9/0.99/0.99999999, and tillage depths
0/0.3/1/2 m. Rounded input demands exceeding original inventory were excluded
from this feasible-state sample; permanent dry-profile tests cover failure.
Every run completed with nonnegative stores and zero unallocated remainder.

The actual binary32 storage-change residual never exceeded the sum of half-ULPs
of final stores plus a conservative binary64 operation bound:

    bound = sum(0.5 * ULP(final_store))
            + gamma(40*n + 10) * (initial_inventory + demand)
    gamma(k) = k*epsilon64 / (1-k*epsilon64)

The maximum absolute residual was 3.893202205063062e-9 m, within this independently
defined bound. The factor 40 operations per layer conservatively covers both
passes, inventory summation and final conversion; it was not fitted to a failing
case. Native probe, input/output records, hashes and receipt are retained at
`/workdir/watershed-physical-water-repair-20261021/reviewer-signed-allocation/`.
This is supplementary stress evidence; the portable targeted regressions remain
the mandatory reproduction.

Full-period receipt inspected:
`/workdir/watershed-physical-water-repair-20261021/hill-lane-results.json`.
It contains six groundwater runs and four hourly-lane/daily-control runs;
all complete 1980–2023, and the hourly lane's daily control is byte-identical.
Those receipts precede the review-driven signed-allocation changes and must
not be presented as validation of a later binary without a new hash/replay.

Remaining coverage includes native post-percolation/frozen/saturation accounting,
variable OFE widths, and direct
multiple-hillslope COMMON-index controls. The complete source/routing/storage
issues in `scientific-preflight-review.md` remain open. No dated release,
vendoring, deployment or universal watershed correctness is approved here.
