# Hillslope Water Aggregation Contract

## Scope and status

Approved scope: operator requested correction of MOFE ET/Dp consumers and then
execution of the work package on 2026-10-20. Implementation conformance is pending.
This contract governs local water fluxes in hillslope water-balance reports,
dashboard event ET (selected and comparison runs), and H.wat Features Export.
It amends the historical numerical preservation rule in the
[output-scope contract](output-scope-contract.md#hillslope-water-balance-summary-cache)
and the [cache freshness contract](report-cache-freshness-contract.md).

## Numerical contract

H.wat Ep, Es, Er, and Dp are local OFE depths in mm; Area is local OFE area
in square meters. For each reported hillslope and simulation day, each local
flux is `sum(depth * Area) / sum(Area)`. ET is the sum of the three weighted
components. Compute daily depths before summing days into years or averaging
years. Never divide annual accumulated volume by accumulated area-days.
Merge native IDs mapped to the same report hill before daily division.
Single-OFE results are unchanged. Subdivision into equal-state subareas is
invariant. The denominator is the area of the day's represented OFE rows;
sparse days are not padded with fabricated zero observations.

Preserve P, Q, QOFE, latqcc and all other fields' existing aggregation policies,
report labels, units, output columns, scope selection, API signatures, and the
report's `max(number_of_years - 1, 1)` annual divisor. Area_m2 remains the sum
of first-observed areas per native WEPP/OFE mapped to the report hill; model
geometry is stationary. TotalWatSed and the Python daily loader remain controls.

Native reports require sim_day_index (qualified by water_year) for daily
identity. Canonical interchange already supplies it. Missing daily identity is
an explicit input error; do not infer one day per year. Export accepts its
existing date or calendar year/julian daily identities, including supported
legacy OFE column spelling. Daily local fluxes are reduced independently of
terminal-OFE routing measures. Export ET is derived from Ep+Es+Er before column
selection, without adding a raw parquet column. Advertised ET units are mm.
This applies to baseline, Roads, and AgFields wherever a source is H.wat.
AgFields mixed-source joins retain their existing many-to-many rejection; this
package does not redesign field-to-hill or temporal joins. Test admitted H.wat
materializations and retain an explicit limitation for rejected mixed-source cases.

## Input and absence policy

Populated local-flux rows require finite positive Area. Missing, null, zero,
negative, or infinite Area is an explicit calculation/materialization error;
never substitute equal weights or terminal depth. Native and export null/NaN
flux values retain zero-contribution semantics; infinity and arithmetic overflow
fail. Dashboard null/NaN components contribute zero; infinite components or
nonfinite weighted results yield unavailable ET, matching its invalid-area policy. Dashboard invalid area produces null ET (unavailable), never a misleading
numeric map value. Range, difference, tooltip and color consumers must preserve
unavailable ET instead of coercing null to zero. Empty selected datasets keep existing empty/null outcomes.
OFE identifiers are required for native report area accounting. Repeated daily
OFE rows are malformed upstream data; this change does not add a general raw
interchange deduplication policy. Existing consumer duplicate checks remain.

## Cache compatibility and recovery

Keep report filenames, schemas and version-1 provenance envelopes. Add an
aggregation marker `mofe-area-v1` to native summary schema metadata and report
proof metadata. A cache lacking that marker cannot be verified current. With
source and translator available rebuild it through the corrected native writer;
verify the writer's marker before publication. With dependencies unavailable,
retain existing explicit historical_unverified access and warning. Never label
an old numerical cache current merely because its source hash matches. If the
native API is unavailable, retain the existing source-newer-than-cache guard
and explicit historical_unverified fallback; newer source still fails. This
exception does not permit a callable old writer to publish an unmarked result. A fresh
native writer lacking the marker fails without replacing the published cache.
Features Export changes its export version marker so prior products are not
reused under the corrected algorithm. Original archived bytes remain historical;
restoration uses the same freshness rules. No bulk deletion or production repair
is authorized. Rollback must pair the native writer and Python consumers.

## Regression obligations

Areas 250/750, Ep 1/4, Es .5/1, Er .5/1, Dp 4/8 yield Ep 3.25, Es .875,
Er .875, ET 5 and Dp 7 mm for one day; two days yield ET 10 and Dp 14.
Exercise merged translator IDs, unequal-area hills, subdivisions, sparse dates,
multiple years, single OFEs, baseline/comparison event SQL, export event/yearly/
annual-average and selected columns hiding Area. Read serialized outputs and
cold/warm/stale/historical report artifacts, including failed native publication.
Validate existing routing metrics separately so the local-flux correction cannot
silently change their semantics. See ADR-0098 for decision rationale.
