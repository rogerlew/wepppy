# Independent review of the complete R4 event ledger

Disposition: **accepted as a paired observational ledger**, not parameterization
acceptance or a single-parameter causal experiment. Review covers all 116 cases
and both lanes, after the complete results became available. This is independent
AI scientific review, not institutional peer review. No production source,
native execution, soil input, threshold or parameter changed during this review.

## Independently verified scope

`review_event_supply_ledger_r4.py` imports neither the ledger implementation nor
its historical audit helpers. It freshly checks 2,900 original input files and
1,624 native outputs; all records use the exact R4 engine. Paired core input sets
match and only `p1.sol` differs. The supplemental projection check confirms all
116 legacy soils remain byte-exact copies of their originals, in format 98.4;
these are 21 distinct decks, not 116 independent material replicates.

All 4,067,424 lane/OFE/day rows have complete, unique declared calendars and
matching paired precipitation. Surface outflow uses cumulative Q and cumulative
emitted area; runon, lateral flows and other local depths use local emitted
area. SedLeave is kg/m times width. Stock, NULL missing ELEMENT support and
undefined concentration/delivery denominators are retained without zero filling
or epsilon division. Missing reported contributions receive zero only in the
explicit reported-sum decomposition, not in physical mass/state fields.

There are 8,352 independent accurate-sum annual flux comparisons against both
persisted ledger aggregates and historical accepted audits. Maximum aggregate
reassociation difference is 4.148e-10 in the relevant native quantity's units;
all differences lie inside accumulated IEEE rounding bounds. This verifies
analysis algebra, not a new model tolerance or a closed watershed budget.
The separate 11,832-value projection check confirms only the twelve integrated
flux fields are annualized; counts, OFE identifiers, geometry, states and ratios
are not divided by years.

The emitted-width versus metadata-width difference is correctly handled as a
serialization boundary: exact Decimal half-last-place intervals bound the
emitted slope tokens. Physical ledger quantities use emitted geometry; historical
sediment audits retain their original record width, with an explicit linear
width-ratio bridge. Historical water audits already use emitted areas. No
arbitrary `isclose`, input rewrite or scientific acceptance relaxation is used.

Native ELEMENT Ki/Kr are effective, adjusted event values. The writer prints
Ki divided by 1e6 and Kr multiplied by 1e3. Retaining raw columns and defining
`Ki_effective_SI = printed_Ki * 1e6` and
`Kr_effective_SI = printed_Kr / 1e3` is correct; these are not unadjusted soil-file
parameters. Current reader unit labels omit this numerical scale. The ledger
corrects its own interpretation without modifying production readers.

The complete ledger retains 2,131 unavailable Sm diagnostics and the existing
strict modern fraction flag on site/2711250/outunrut/paved/low, 2003 day 29.
These are not silently repaired or waived. No missing ELEMENT with positive
surface flow or positive sediment with zero surface volume appears in the
reported coverage check. The required accounting fields remain available.

## Particle and event interpretation

The independent verifier recomputes terminal clay fractions from **EVENT-only**
sediment masses. SUBEVENT/no-event composition is absent, and a zero EVENT mass
denominator remains undefined. These diagnostics are not fractions of all
annual export and do not identify incoming or per-OFE particle mixtures.

The printing-separated event diagnostic correctly requires both the reduced
incoming mass and increased outgoing mass to exceed the sum of two native
half-F9.3 intervals: 0.001 kg/m times the shared emitted width. Raw sign counts
remain distinct. This is an interpretation check, not a changed particle or
physical acceptance gate.

Two selection qualifications must accompany downstream use:

- The frozen top-three artifact ranks the largest **signed** differences, despite
  the declaration's “largest positive” wording. Of 348 rows, 152 are nonpositive:
  144 in meaningful-low cases and eight in small-exceedance cases. Preserve the
  artifact, but do not treat zero/dry rows as positive-discrepancy observation
  seeds. A later source-observation declaration must select actual supported
  events explicitly.
- Only 37 of 38 paved cases have exact zero reported road export in both lanes.
  Denver/2711184/outrut/paved/none has 0.001485 kg/yr legacy and 0.0002475 kg/yr
  generated road export. It is not a literal zero-road-sediment control; no
  threshold is used to relabel those values zero.

Neither qualification invalidates the persisted accounting. They constrain its
scientific interpretation and future experiment selection.

## What the complete panel supports next

All 43 small-reference exceedance cases export more sediment with generated
profiles than with legacy profiles. In 28, generated profiles nevertheless
supply less sediment from the fill to the buffer. There are 115 buffer events
in this group with both differences larger than printing uncertainty. Median
paired annual fill export decreases 10.426 kg while terminal export increases
5.434 kg. This supports investigating buffer transport/retention and local bed
exchange together; it does not prove excess buffer erodibility. Less deposition,
more local production, different incoming classes and different hydraulics can
produce the same net-boundary pattern.

The pattern also occurs in 13 of 18 meaningful passing controls, so it is not
itself a failure criterion. Conversely, all 48 meaningful-underprediction cases
export less with generated profiles, and 44 supply less sediment from the fill.
A uniform erosion reduction is therefore unsupported by this complete panel.

The next bounded experiment should observe actual incoming/outgoing class loads,
water discharge/shape, transport capacity, and separately integrated local
production/deposition on declared buffer events and matched passing controls.
Include a separate underprediction supply case selected from actual negative
contributions, not the zero-ranked top-three rows. Preserve paired full-period
ordinary-output parity. Event-only terminal clay statistics cannot substitute
for the missing incoming class observations, and regional EBE detachment/
deposition averages cannot be multiplied by whole area to invent gross exchange.
No coefficient, soil writer change or parameter candidate follows from this
observational result alone.

## Evidence

- `event-supply-ledger-r4-independent-readback.json`: full-calendar, unit,
  source, ratio, particle-support and annual checks.
- `event-supply-ledger-r4-projection-review.json`: field-specific annualization,
  original legacy soils and actual paved boundary exports.
- `event-supply-ledger-r4-independent-acceptance.json`: exact script, declaration,
  result and review hashes with the scope qualifications above.

Reproduce from WEPPpy using the existing environment:

```bash
.venv/bin/python docs/work-packages/20261029_roads_parameterization_program/artifacts/review_event_supply_ledger_r4.py --root out/roads-parameterization-program-20261031/event-supply-retention-r4-v3 --output /tmp/ledger-independent-review.json
python3 docs/work-packages/20261029_roads_parameterization_program/artifacts/review_event_supply_projection_r4.py --root out/roads-parameterization-program-20261031/event-supply-retention-r4-v3 --output /tmp/ledger-projection-review.json
```
