# U10 independent capacity review

Independent AI review. The reviewer authored native controls and tests, but did
not edit the three production model units. **No remaining bounded implementation
or accuracy blocker was found in U10 source `ba9f2ad91`.** Full actual-binary
validation and scientific watershed disposition remain required.

## Confirmed shared defect

Both TRNCAP and YALIN used the REAL expression
`1 - log(1 + sigma) / sigma`. Rounding the addition can make the result negative
near the positive transport threshold. The physical factor is
`integral[0,1] sigma*t/(1+sigma*t) dt`, hence lies between zero and one for
positive sigma. It has the zero limit zero and series
`sigma/2 - sigma^2/3 + sigma^3/4 - ...`.

Fixture-first commit `a8780759b` retains actual TRNCAP/YALIN calls linked with
actual SHIELD and portable math. Five physical classes and positive shear yield
180/288 negative channel capacities and 146/288 negative hillslope totals at
each of O0/O2. Observation-only operand logging preserves native outputs exactly.
The oracle evaluates the equation at captured REAL-rounded operands using
90-digit Decimal arithmetic. No downstream clipping or surrogate constitutive
function establishes the failure.

## Repair and native validation

Both callers now use the shared YALINF companion in the already linked SHIELD
unit. It evaluates the series with double intermediates below 0.01, the direct
double expression otherwise, and returns REAL. The 12-term truncation near the
selector is far below REAL rounding error. The selector is numerical, not a
new physical calibration. The edits retain delta, class weighting, the incoming
QS floor, sand adjustment and the existing capacity-allocation iteration.

The separate green generator replays all 1,152 frozen controls with unchanged
inputs and high-precision references. All capacities are positive; maximum
errors are 1.962 REAL ULP for TRNCAP and 2.322 ULP for YALIN. All red artifacts
remain byte-identical to their committed versions.

Permanent `tests/test_yalin_stable_capacity.py` passes 80 checks across O0/O2.
Coverage includes zero, subnormal/tiny inputs, neighboring REAL values around
the selector, large finite sigma, monotonicity and a 180-digit factor oracle
within one REAL ULP. It also executes both complete consumers, preserves the
QS floor and class fractions, checks mixed-supply redistribution and sand
weighting, and replays the exact unequal-class Cedar frame. The extra-policy
driver initially printed all ten allocated particle slots; selecting the five
active classes corrected that test-harness assumption without a model edit.

## Exact Cedar producer replay and scope

The observed frame is channel 363, 1986 day 209, segment 4. Its
fifth class has sigma `0.00018666169489733875` and negative native capacity
`-2.0561512562022877e-11` lb/s/ft. The frozen U9a routine reproduces all five observed
capacities bit-for-bit at O0/O2. U10 returns five positive capacities matching
the independent equation, including `2.7487030172449042e-15` for the fifth class.
The completed observer replay matches all nine standard output hashes and all
77 violation lines. Its causal receipt identifies 34 first-negative productions
from positive-sigma negative TRNCAP capacity before CASE12 (28) or CASE34 (6),
plus 43 propagated negative inputs. Thus the retained frame has complete
observation provenance; post-U10 full-period sign validation remains separate.

The effect is not limited to the tiny negative number. In the old frame that
negative fifth-class factor triggers redistribution that suppresses the first
four capacities to the `1e-31` incoming-load floor. With the corrected factor,
all intrinsic capacities exceed their incoming supply; the existing algorithm
returns approximately `1.75e-4`, `6.81e-5`, `1.70e-4`, `3.37e-5` and `2.75e-15`.
This is a consequence of restoring a valid producer input to the unchanged
allocation algorithm. Broad hillslope, Roads and channel output changes must be
measured afresh; the preceding channel-only output-parity claim cannot transfer.

## Evidence and acceptance boundary

The incident `artifacts/repro/` directory retains
`review-U10-independent-tests.json`, `review-U10-capacity-green.json`,
`review-U10-Cedar-capacity.json` and the exact Cedar input, alongside original
red evidence. The public scientific account must describe both affected consumers
and the allocation consequence. The full-channel sign audit must still exclude
another downstream producer defect. This review does not approve release,
vendoring, field calibration or relaxation of Roads magnitude criteria.

## Actual dated-pair local gate closure

The canonical system-toolchain dated build pins model source
`ba9f2ad91b5165d5cd2954bd64b5df608798541e`. Its watershed SHA-256 is
`819b91721f67c4a86a5ecea14c5beb840e9a705025da2a2cedf2b97a5e067715`;
the hillslope SHA-256 is
`21d8480041d2efed942abb8471271ce1a11c5f72190d45c0c42dbe0028c019ed`.
All 506 declared source/support files and the frozen, active and dated binary
copies match. The original WEPPpy installed pair and sidecars remain unchanged.

On these actual bytes, the complete native suite passes 1,059 tests in 615.74
seconds, with two existing tarfile deprecation warnings. All 18 hillslope
watchlist cases and both three-year host smoke runs pass. ELF provenance uses
the system loader and libraries; the ablation artifact-policy gate also passes.
Permanent focused tests and their proof generators are committed as `2934a24b8`.
The separate WEPPpy re-release package retains the five complete logs,
`artifacts/native-U10-gates.json`, and its executable verifier. This evidence
does not transfer the earlier U9a Roads or Cedar results to U10.

Independent verification of the fresh U10 Roads run matches all 840 case IDs,
10,080 frozen inputs and 5,880 native output hashes; all 840 complete and pass
their physical/accounting audits. The separate magnitude groups remain below
their frozen acceptance requirements: 719/766 meaningful-reference cases
(93.864%) and 30/74 small-reference cases (40.541%). The aggregate 749/840 is
descriptive only. Annual-export metrics match U9a, while some daily and other
native outputs change. All 99 Disturbed tests pass, covering 96 simulations and
768 retained output files. The re-release package retains
`artifacts/native-U10-broad-gates.json` and the independent verifier. Final Cedar
scientific disposition and the post-repair channel-sign audit remain separate
acceptance gates.
