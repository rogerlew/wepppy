# Revised Roads sensitivity results

All 47 declared native profiles completed with passing physical, full-calendar
and unchanged strict EVENT particle audits. The exact generated control
reproduced all seven retained r7 outputs byte-for-byte. The panel contains 47
actual distinct slope/soil/management/climate signatures, plus 12 preparation-only
alias probes. This supports bounded characterization of existing controls;
it does not establish field calibration, promote generated soils or change defaults.
Independent outcome review passes for this bounded scope.

[Protocol](revised-sensitivity-protocol.md),
[machine summary](revised-sensitivity-summary.json),
[reproducible summary reader](summarize_revised_sensitivity.py),
[preexecution scientific review](revised-sensitivity-preexecution-review.md),
[harness QA](revised-sensitivity-harness-quality-review.md), and
[calendar guard QA](revised-calendar-context-quality-review.md).
[Final scientific review](revised-sensitivity-science-review.md) independently
rechecks all 47 outcomes; its [readback receipt](revised-profile-independent-science-readback.json)
retains the raw verification.
Raw evidence is retained at
`/wc1/runs/ro/roads-parameterization-program-20261103/revised-sensitivity-v1/`.
Its final `declaration-v6.json` SHA256 is
`833ceb1c08b61bb72ef0085171f2dea14958b39dfc6ccce552a671324c8a2afe`.

## Scope and controls

H/L/P are production-template rutted silt/gravel/none, sand/paved/none, and
loam/gravel/low contexts. U is production-template unrutted silt/paved/high.
They use the committed site climate, 2000–2015. G is the separately conditioned
generated-material rutted Denver/2711184/gravel/high research context, with its
actual simulation calendar years 1–16. No reserved material was used. The earlier
outunrut research capsules were not transplanted into production topology;
[role disposition](revised-research-role-disposition.md) explains why.

The table shows production PASS-derived mean annual profile sediment export,
kg/year. It is neither road-only loss nor routed watershed export. Requested
baseline width/fill length/fill slope are 4 m/30 m/10% for H/L/P/U and
3.96 m/4.57 m/50% for G. All paired comparisons use their own baseline.

| Arm | H | L | P | U | G |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline | 36.781946 | 0.103512 | 4.767988 | 36.749406 | 0.068707 |
| Width 2 m | 18.390943 | 0.051756 | 2.384001 | 18.364683 | 0.034701 |
| Width 8 m | 73.563750 | 0.207023 | 9.535968 | 73.478728 | 0.138804 |
| Fill length 10 m | 15.299446 | 0.103265 | 4.642237 | 34.770831 | 0.471924 |
| Fill length 60 m | 68.619754 | 0.183426 | 5.866794 | 43.882111 | 30.362213 |
| Fill slope 2% | 23.410539 | 0.080900 | 4.496466 | 31.630590 | not studied |
| Fill slope 30% | 56.732650 | 4.478071 | 9.855795 | 73.492352 | not studied |
| Width 8 m + fill 60 m | 137.240107 | 0.366854 | 11.733591 | 87.740068 | 61.337085 |

Width primarily scales modeled area and extensive water/sediment quantities in
these contrasts. Density responses are nearly unchanged; serialized unrutted
width precision also matters. Increasing fill length changes both contributing
area and modeled process extent. H sediment density increases from 0.146846 to
0.185219 kg/m²/year at fill 60 m, while P decreases from 0.0190354 to 0.0158357
and U from 0.304469 to 0.249600. A change in total export alone is therefore
not evidence of an improved erosion rate.

Fill slope is consequential: L changes from 0.080900 kg/year at 2% to 4.478071
at 30%. These finite contrasts do not validate the full input range or provide
recommended/calibrated values. G's large fill-length response is geometry
sensitivity on a previously underpredicting comparison context, not a fitted
rescue or a default proposal.

Traffic is a coupled categorical choice, not a monotonic mitigation slider:

| Traffic | H | L | P | U |
| --- | ---: | ---: | ---: | ---: |
| High | 15.750158 | 2.180502 | 12.519465 | 36.749406 |
| Low | 4.909538 | 0.828163 | 4.767988 | 10.830532 |
| None | 36.781946 | 0.103512 | 25.124255 | 11.650603 |

Low and none share emitted soil erodibilities but select different management
conditions. H's initial residue indices change from `[1,2,1]` to `[2,1,1]`;
this couples roles and can reverse simple expected rankings. These observations
must not be presented as recommending traffic increases to control erosion.
All four inslope preparation probes have exactly unchanged native inputs when
fill length changes to 60 m. They are confirmed fill-control no-ops. Low-to-none
traffic changes management bytes even there; it is not a complete input alias.

## Water, events, roles and interaction

Baseline PASS runoff volumes for H/L/P/U/G are respectively 84.101912,
29.808812, 61.228691, 43.957508 and 0.028157 m³/year. Full daily water, event
ELEMENT/EBE, yearly PASS responses, signed role exchanges and native OFE areas
remain in each case's `response.json`, `audits.json`, `annual.parquet` and raw
interchange tables. `analysis.json` retains each paired input difference,
requested/effective/emitted geometry, largest event changes, annual changes,
role-boundary deltas and alias identities. Nonbaseline contrasts affect between
1 and 422 daily PASS records in this panel.

The extensive width-by-fill interaction includes area multiplication. Its
sediment-density difference-of-differences is at most 0.000002715 kg/m²/year
in absolute magnitude across the five contexts. This is consistent with near
width scaling here; the nonzero extensive interaction is not evidence of a new
physical synergy. Expected directions were not acceptance predicates.

Native geometry consumption is checked through WAT local OFE area readback.
Canonical soil/management readers verify emitted values and scenario ownership;
selected native `input.for`, `init1.for`, `contin.for` and `wshpas.for` bytes are
bound in the source snapshot. All runtime UI, groundwater and PMET markers pass.
Complete sidecar membership is checked. Water transfer checks do not claim a
complete storage closure, and role net exchange is not tagged particle origin.

## Generated bridge and output definitions

G's exact retained run has PASS export 0.0686837246 kg/year. The canonical slope
writer bridge changes aspect from 100 to 180 degrees and serialization; its
PASS export is 0.0687073758. This bridge is reported separately from the width
and fill contrasts. Its raw source outputs remain unchanged.

Historical G export 0.08712 kg/year is the printed LOSS mean, not the production
PASS summary above. Current exact readback establishes:

- ELEMENT terminal total: 0.0853875 kg/year.
- One positive terminal non-EVENT day: 0.0165825 kg/year.
- EVENT-supported ELEMENT total: 0.068805 kg/year.
- PASS EVENT export: 0.0686837246 kg/year.

The EVENT difference is 0.0001212754 kg/year, within the single printed ELEMENT
event half-unit 0.00012375. LOSS minus ELEMENT is 0.0017325 kg/year, within the
annual LOSS half-unit 0.00198. Native `wshpas.for` publishes EVENT particle payload
at terminal runoff at least 0.001 m; the positive non-EVENT day has no such payload.
All 47 LOSS/PASS/ELEMENT/non-EVENT totals are retained in the machine summary.
This is an explicit support/precision reconciliation, not a relaxed criterion or
an internal-conservation claim. Strict EVENT audits do not certify non-EVENT
particle composition.

## Retained failures, correction and execution identities

There were exactly 47 new profile-study native calls: 1 under declaration v2, 40 under v3 and
6 under v6. No successful native execution was silently repeated. Native binary
hashes remain the installed r7 pair specified in the protocol.

The first canonical profile completed natively but its inherited study reader
expected yearly LOSS text that the canonical abbreviated deck does not request.
The existing reader's explicit abbreviated mode now applies only to the template
lane. Complete PASS/WAT calendars and yearly tables remain required. A subsequent
read-only check also exposed normalized research CLI-header identity versus the
unchanged canonical fixture; each lane now binds its actual CLI.

G's exact native replay matched all seven files but initially failed postprocessing:
the temporary template project retained a site 2000–2015 ancestor calendar while
native G consumed years 1–16. Owned EBE/WAT readers discover that ancestor calendar;
ELEMENT used its explicit start year. The wrong leap-year mapping shifted dates.
The original failed G tree remains intact. New `recovered/G/` contexts copy exact
native inputs, provide the matching calendar and reuse exact native outputs.

The maintained harness now rejects a wrong/aliased/nearer reader context, a
changed declared native CLI, and stale cached calendar dates before native
execution or summary. It uses the owned discovery/CLI parser, compares full
calendar columns, and never deletes or repairs a cache silently. Real-filesystem
regressions cover rejection and the valid path. Final helper/contract validation
passed 21 tests; independent QA repeats that result. The late guard was applied
retrospectively to all 47 contexts and before the final six native calls. It was
not present during the first 41 calls. Prior source snapshots, declarations,
unused approvals, failed receipts and reader-check attempts are preserved.

## Reproduction and limits

The final continuation and analysis commands are:

    wctl exec weppcloud python docs/work-packages/20261029_roads_parameterization_program/artifacts/revised_sensitivity_generated_continue.py run --declaration declaration-v6.json --review generated-continuation-v6-review.json
    wctl exec weppcloud python docs/work-packages/20261029_roads_parameterization_program/artifacts/revised_sensitivity_generated_continue.py analyze --declaration declaration-v6.json --review generated-continuation-v6-review.json
    python docs/work-packages/20261029_roads_parameterization_program/artifacts/summarize_revised_sensitivity.py

These write exclusively and refuse to overwrite retained results. For a new
study, use `tests.roads.roads_sensitivity` with a new exclusive root and a reviewed
new declaration; do not retarget frozen manifests. Every raw case and earlier
attempt remains readable without rerunning the engine. The independent outcome
reader provides a separate read-only validation route.

The 40 production profiles use one site climate and a small geometry/texture
panel; G adds one compatible generated material and a separate climate. Inslope
probes establish preparation semantics only. The companion
[project protocol](revised-project-sensitivity-protocol.md) covers public-controller
propagation and baseline preservation separately. None of this is browser/RQ or
deployment parity. Numeric validity bounds, studied contrasts and field-calibrated
ranges remain distinct. Human specification/layout approval is still required
before production configuration persistence or view implementation.
