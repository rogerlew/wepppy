# Source audit and interpretation boundaries

Source commit: `b73e93b19a724d1991d341d38a18d11e742231bd`, the retained provenance
for exact `wepp_261026`. Frozen input.for, scon.for and watbal.for are under the
execution root's `native-source/`, with SHA-256 values in declaration.json.
The follow-up routing audit extracted irs.for from the same commit into
`reconciliation-v2/native-source/irs.for`; its identity is in source-audit.json.

## Depth and initial storage

`input.for:564–572` adds 200 mm to the last input cumulative horizon depth.
Line 591 caps it at 1800 mm. Lines 698–728 populate whole 200 mm computational
layers up to the adjusted bottom. For the frozen inputs this predicts:

| Input bottom, mm | Adjusted bottom, mm | Computational bottom, mm |
|---:|---:|---:|
| 399 | 599 | 400 |
| 400 | 600 | 600 |
| 401 | 601 | 600 |
| 1599 | 1799 | 1600 |
| 1600 | 1800 | 1800 |
| 1601 | 1800 after cap | 1800 |

Every native WAT readback confirms its predicted depth. Both sides retain the
explicit 200 mm input boundary and identical material properties. This probes
representation sensitivity; it does not propose subtracting 1 mm from production
soil files or prove the physical soil is 400 rather than 600 mm deep.

`scon.for:510–515` initializes water from saturation fraction, porosity,
coarse-material factor and layer thickness, with a lower-bound clamp. Initial
input saturation stays 0.75 throughout; changing computational depth necessarily
changes absolute storage. Years 2–16 exports are retained to assess persistence,
not as a claim of equilibrium or a newly calibrated warm-up period.

## Restrictive-layer conductivity

`input.for:665–675` consumes 9002 `kslast` in mm/h, dividing by 3.6e6 to get m/s;
restrictive-layer thickness is converted from mm to m. Thickness, flag and all
horizon conductivities are fixed across each drainage pair.

The SSURGO writer explicitly applies `(source_um_s * 3.6) / 1000` as a historical
bedrock proxy, or 0.01 mm/h where no restrictive layer was identified. This was
not discovered as a new unit-conversion error. See the authoritative
[SSURGO history](../../../../wepppy/soils/ssurgo/ssurgo.md#historical-kslast-parameterization-git-record).

Frozen sand provenance identifies a lithic restriction at 0.42 um/s; clay
identifies a low-conductivity horizon at 0.91 um/s and restriction type N/A.
The alternatives are 1.512 and 3.276 mm/h, calculated from those source values,
not by multiplying rounded emitted values by 1000. Loam has no detected
restriction, so 59.8734 mm/h is its deepest emitted horizon Ksat. This last
endpoint is a no-throttle counterfactual, not measured bedrock conductivity.
None of these alternatives is accepted as a physical lower-boundary condition
merely because sediment moves closer to a generic FSWEPP reference.

## Upstream coupling

The initial analysis demanded exact upstream output equality and failed. Road
and fill consumed soil objects, management, geometry and climate remain unchanged,
but 14/24 cases have upstream output differences. No epsilon or tolerance was
introduced to call them invariant. All differences are retained by field and OFE,
including date counts, maximum absolute differences and signed sums. Sparse
ELEMENT date unions treat a missing row as zero load for flux comparisons only;
calendar differences are counted separately. State comparisons use common dates.

The exact source provides an explicit reason not to assume sediment independence:
`irs.for:742` calculates effective runoff duration for an equivalent hydrologic
plane; lines 753–777 assign that duration and recompute peak runoff for all its
member OFEs. A downstream change can therefore change upstream erosion forcing.
`sloss.for:165–224` uses effective duration in boundary sediment-load computation,
as audited in the preceding study. ELEMENT PeakRO and EffDur differences are retained.
This establishes a coupling mechanism, not an event-by-event trace of every
observed change. Small upstream water/state differences, including larger daily
fill differences in depth-perturbed Denver, remain observed but not fully traced.

Run prompt ends with ipass=0: small-event routing is enabled. Do not invoke the
passby skip as an explanation for this experiment without an internal trace.

## Budgets

Reuse the preceding exact-release
[sediment/water semantics](../../20261029_roads_ofe_budget/artifacts/output-semantics.md).
All 24 terminal ELEMENT/annual report budgets reconcile within the unchanged
precision bounds; there are no beyond-precision EBE discrepancies in this panel.
Net sediment exchange is not gross detachment/deposition or particle provenance.
WAT Q uses cumulative area; lateral terms and upstream inflow use local area.
Apparent soil balance is not full canopy/snow/soil mass closure.

The near-capacity diagnostic counts days when reported SoilWaterTotal is at least
90% of reported ProfilePorosityCap. It is a descriptive storage proxy, not an
independent proof of the saturation-excess runoff mechanism or a model threshold.
