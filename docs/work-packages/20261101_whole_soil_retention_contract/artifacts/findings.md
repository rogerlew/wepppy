# Whole-soil retention audit findings

## Decision

The current SSURGO mass-complement reversal is not generally the inverse of the
native volume-share correction. A bounded preparation prototype and native
consumer audit are justified next. Neither a volume inverse nor a global
porosity multiplier is ready for promotion. No production parameter, native
source, default, surface-cover policy or existing project changed here.

The durable [capacity contract](../../../schemas/whole-soil-water-capacity-contract.md)
records this decision and its source, artifact and native-domain requirements.

## Actual preparation and serialization

Current NRCS acquisition retained 39 horizons and 61 separate fragment records
from four admitted development mapunits. These are current source records, not
historical model inputs. The declared 72 attempts comprise those 39 horizons and
33 synthetic controls. Actual Horizon and real Rosetta executed in the supported
weppcloud container. Actual 7778 write() and WeppSoilUtil readback used a controlled
single-horizon context, not actual mapunit/profile selection.

| Panel | Serialized | Serialization unavailable | Construction unavailable |
| --- | ---: | ---: | ---: |
| Current source horizons | 27 | 6 | 6 |
| Synthetic controls | 33 | 0 | 0 |

The six construction failures explicitly report missing clay. The six other
exclusions have unavailable rock and fail Horizon.valid(); their Rosetta values
and notes remain retained. All 27 serialized source horizons used the preferred
source branch for both retention values. The synthetic panel exercises each
single-value fallback, both missing, pair sanitization, missing density, zero
retention, mass-cap neighborhoods and the native85% cap projection. Sixty actual
files retain all emitted 200 mm split rows, FC/WP four-decimal and BD/RFG
two-decimal readback, plus CRLF evidence. No native execution occurred.

## Quantitative diagnostic

For source-density1.3 g/cm3 and fragment-density2.65 g/cm3, the pre-guard
CPM/current-mass-complement ratio is1 at zero rock,1.341772 at50% mass and
0.932551 at70% mass. Direction therefore reverses; a universal inflation claim
would be incorrect. These values are conditional arithmetic, not final native
retention or runoff effects.

At95% mass and source FC0.30 the nonporous volume inverse is3.096226, an
incompatible assumption/source combination. The separate native85%-cap
projection gives CPM0.264559 and projected FC0.158735 using the emitted FC0.60.
Do not confuse uncapped source-density diagnostics with capped emitted-density
projections or clip the inverse to manufacture agreement.

Exact arithmetic controls show ordered dry/field/saturation limits and FC/UL2/3
can coexist with UL-DRFC=0 after a proposed volume-scaled ceiling. Zero-rock
identity and the singular conductivity log at ratio1 are separately checked.
These are algebraic counterexamples, not compiled native evaluations.

## Evidence interpretation and known metadata erratum

In audit-v1, the boolean named source_native_density_equal_assumption in
emitted_cap_projection means **hypothetical native density equals emitted,
rounded BD**. It does not mean original source density equals native density:
source density may be missing, estimated or rounded. The executed helper and
receipt are preserved without rewriting. source_basis_diagnostic uses original
source density only when available. All projections explicitly say
native_executed=false. This erratum governs interpretation of that legacy key.

Source/prepared/emitted records, loaded dependency and Rosetta asset hashes,
source response receipts and excluded records are retained in the private raw
root out/whole-soil-retention-20261101. Readback and scientific reviews accompany
this package. No whole-watershed accuracy, porous-fragment law, annual water
budget or deployed behavior is claimed.

## Next experiment

Compare a separately declared volume-inverse preparation prototype against the
current heuristic using source-bound generated files. Record source/density
incompatibilities explicitly; specify zero/missing/fallback compatibility in an
ADR. Trace native retention guards, density recomputation, air adjustment,
conductivity and drainage domains, then test complete histories with accepted
flux and overflow ownership. Only that evidence can support a production change.

## Checkpoint validation

Independent scientific and implementation reviews accepted the bounded claims.
Five deliberate record corruptions were rejected; three exact domain controls
passed. All5802files in six preceding raw roots remain unchanged. All272members
of the new private archive were hash-verified against the frozen raw inventory;
see [archive receipt](archive-receipt.json). Scoped documentation lint passed.
No application test suite was needed for these research helpers and contracts.
