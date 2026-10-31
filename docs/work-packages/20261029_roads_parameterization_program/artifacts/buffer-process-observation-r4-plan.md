# Revision-4 buffer process observation

Status: proposed bounded source-observation study; deterministic selection has
read the completed ledger, but no observer has been built or executed. Independent
scientific and implementation review precede instrumentation/execution.

## Question and exclusions

Explain the selected same-engine soil-profile differences in surface-flow
support, sediment delivery and local exchange before considering parameter
changes. The verified ledger has 115 small-group case-days with less generated
incoming sediment but more outgoing sediment beyond native print intervals;
all have more generated outlet water and peak runoff, and 101 have zero legacy
outlet water. Forty-two have less generated incoming surface water. The same
annual sediment signature occurs in 13 of 18 meaningful passing controls,
while all 48 meaningful underpredictions have less generated outlet sediment.

The experiment compares complete legacy and generated profiles at revision 4.
The generated lane is the existing U12 `erosion_road_cap` candidate, including
its previously declared road erosion and upper-200 mm conductivity conditioning;
it is not an unmodified SSURGO profile or a new treatment.
It does not isolate one coefficient or establish that legacy behavior is more
physical. Legacy anchors themselves retain 17 original-benchmark failures.
There is no parameter search, input translation, role mixing, native repair,
WEPP2010 event comparison, withheld material or default/UI change. Neither
terminal clay fractions nor a whole-profile pore-space subtraction can identify
the cause. Previous-day published states are descriptors; actual storm-time
layer states, rates and branches are required.

## Deterministic detailed-event panel

Selection is frozen in [the source-free seed declaration](buffer-process-observation-r4/seeds.json)
and its original [selector](buffer-process-observation-r4/select_seeds.py).
Each ordered stratum selects the largest positive or most negative reported
daily outlet difference, then case ID/year/day. Both ELEMENT observations must
exist, and the outlet difference must exceed the unchanged combined F9.3 print
interval. Cases are distinct. Extra lower-supply conditions use the same
printing-bound diagnostic; no audit threshold changes.

| Stratum | Case | Calendar year/day | Generated minus legacy outlet kg |
| --- | --- | --- | ---: |
| Paved, actual zero road source, legacy dry outlet | Denver/1718465/outunrut/paved/high | 16/127 | +54.183 |
| Gravel, less generated water and sediment inflow | Flagstaff/1718494/outunrut/gravel/high | 5/320 | +79.960 |
| Gravel, legacy dry outlet | Denver/1718494/outunrut/gravel/high | 16/127 | +94.530 |
| Passing control with same annual sediment signature | site/1718465/outunrut/gravel/high | 2015/351 | +121.341 |
| Underprediction with lower incoming supply | site/2711184/outunrut/gravel/high | 2012/324 | −389.585 |
| Underprediction without lower incoming supply | site/2711184/outunrut/paved/high | 2012/324 | −139.575 |
| Small-reference passing zero-road control | Denver/1718465/outunrut/paved/none | 4/233 | +8.061 |
| Meaningful overprediction | site/1856573/outunrut/paved/high | 2012/324 | +178.111 |
| Underprediction outside the core geometry | Denver/2711184/outrut/gravel/high | 16/127 | −195.826 |

These are diagnostic extremes, not representative estimates. The first eight
cases share outsloped/unrutted geometry; the ninth, added before observation,
tests the opposite discrepancy in a rutted configuration. They span three
climates and four generated materials inside the declared five-climate,
seven-material panel. Conclusions about the core process are scoped to
outsloped/unrutted roads; this is not mechanism coverage of all four designs.
Full-panel context remains in the accepted ledger.
For synthetic climates the declared calendar years are 1–16; `site` is
2000–2015. The declaration records both calendar year and native year index.
Do not substitute events after seeing internal traces. Retain empty, missing,
unsupported and contradictory observations explicitly.

## Observations and units

Execute both unchanged soil lanes for the complete original 16-year period:
nine pairs, 18 isolated native runs. Detailed trace output is limited to the
declared target day and the preceding calendar day, including all storm steps
on those days. Preserve a target-day sentinel even when no flow or no erosion
branch runs. Ordinary outputs remain full-period and unfiltered.

Observe all three OFE boundaries to support road controls and fill/buffer
continuity, with detailed layer/routing state at the buffer:

- **Hydrology:** actual incoming and outgoing surface rates/volumes, effective
  contributing length/width, rainfall/melt, effective duration and hydrograph
  timing, routing branch and recession infiltration. Separately record lateral
  inflow/outflow, deep percolation and the explicit surface/lateral coupling
  branch. Do not treat lateral water automatically as sediment-carrying water.
- **Soil state and infiltration:** start/end and active-step layer liquid water,
  ice, temperature/frost-thaw state, saturation/porosity, depth, conductivity,
  restrictions, wetting-front/suction
  state, available infiltration capacity and actual infiltration. Record the
  active layer and branch producing excess/runon/outflow. Distinguish printed
  effective conductivity from the operands actually used by that branch.
- **Sediment boundary state:** actual incoming class loads and outgoing class
  loads at the buffer, bulk load, native normalization factors, discharge,
  settling properties and enrichment state. Record the fill export and buffer
  entry together. Fractions at the terminal PASS writer are not a substitute
  for the incoming state. This is class accounting, not tagged provenance.
- **Local erosion/deposition:** current effective Ki/Kr and critical shear,
  applied shear, transport capacity, interrill contribution, actual signed
  detachment/deposition rates, transition coordinates and load before/after
  each segment. Use actual native integration and scale factors. Do not infer
  gross erosion/deposition from EBE regional averages or boundary net exchange.

Freeze a variable/source/unit map before compilation: name each observation
site, native variable, dimension, normalization and conversion into the emitted
geometry ledger. Start from the exact accepted source's `CONTIN`, `INFPAR`,
`GRNA`, `CONRUN`, `WATBAL`/`WATBAL_HOURLY`, `ROUTE`, `PARAM`, `DETACH`,
`EROD`, `DEPOS`, `ENRICH`, `SLOSS` and output-writer boundaries as applicable.
Read-only mapping must identify the actual call path; listed names do not
authorize assuming unused routines execute. Add a necessary upstream state
site only with an explicit pre-execution map amendment. If a requested gross
term cannot be observed without changing arithmetic, mark it unavailable.

Native lengths/rates may be normalized or per width; retain raw values and
factors before converting to meters, seconds, m³, kg and kg/s. Boundary mass
must reconcile with the full-period ELEMENT/PASS ledger under its original
printing bounds. Do not combine cumulative-area surface depths with local-area
water terms or silently rescale raw printed Ki/Kr.

## Instrumentation and acceptance gates

Use a new ignored source/build/run root and the exact accepted revision-4
source/object provenance. Production source, binaries and inputs are immutable.
Observation-only writes must not modify model variables, expressions, loops,
branches, floating-point flags or optimization. Retain the complete observer
diff and compile/link commands privately; public artifacts contain original
analysis, names, hashes and numerical findings without private source excerpts.

Before any run, bind the selector/seed file, variable map, observer diff,
all contributing source/include/object bytes, compiler/settings, observer binary,
the exact accepted binary and all case inputs. The accepted watershed SHA256 is
`2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48`.
Preserve core and auxiliary inputs byte-for-byte, including reference soil.

Preflight the first declared pair. Require successful full-period runtime,
target-day trace coverage and **byte-identical ordinary outputs** to each
lane's existing uninstrumented revision-4 record. Then run the remaining eight
pairs and apply the same gates to every lane. Rehash sources, inputs and outputs
after execution. Logs must contain normal completion without numerical failure;
observer trace is additional output, never an excuse to alter ordinary files.
Any mismatch rejects that observer attempt before scientific interpretation.
Retain failures; make a new versioned attempt instead of overwriting evidence.

Coverage uses unconditional owning event/OFE/hydrology markers and explicit
entered/skipped branch status. A dry legacy buffer can validly skip sediment
routing; absent ROUTE observations are not inferred zeros or automatically an
instrumentation failure. Each field has a valid-state guard; never print
uninitialized common/local values merely to fill a trace column. Distinguish
valid branch absence from a missing owning marker or missing executed-branch
trace. The latter rejects observer coverage.

Reapply the versioned fixed-width particle audit unchanged. A previously
certified strict flag remains flagged and can transfer only with exact relevant
output parity. New flags require a source-based disposition. No renormalization,
epsilon denominator or relaxed threshold is authorized.

## Decision and stopping rule

For each target day, reconcile the observed boundary ledger, then identify
whether divergence first appears in hydrologic support/rates, incoming sediment
supply/classes, local shear/source or deposition. Compare the same pattern in
passing controls and the opposite discrepancy directions. Observe simultaneous
erosion/deposition only where the native signed integration supports it.

Conclude with either a falsifiable process/input hypothesis for one controlled
ablation, a concrete supported model defect needing its own repair package,
or an explicit unresolved observation gap. Numerical differences between
complete profiles do not by themselves authorize changing real material class
distributions, replacing soils or fitting buffer coefficients. Before matching
an R4 anchor toward a WEPP2010 zero, separately resolve the relevant engine and
reference-contract limitation. Do not execute a parameter ablation in this study.
