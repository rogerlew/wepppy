# Generated RFG basis audit

No volume-to-mass mismatch is established for the selected generated RFG inputs.
The suspected metadata confusion is resolved: `fragvol_r` is volume percentage,
but the emitted RFG path does not use it. `_computeRock` combines `fraggt10_r`,
`frag3to10_r` and `sieveno10_r`; all three have weight-based definitions.

## Primary definitions

USDA NRCS [SSURGO 2.3.2 Table Column Descriptions](https://www.nrcs.usda.gov/sites/default/files/2022-08/SSURGO-Metadata-Table-Column-Descriptions-Report.pdf), printed pp.5–6, defines the two large-fragment groups as percentages by weight of the horizon and sieve10 as weight percentage passing2mm within the less-than3inch fraction. Printed p.4 separately defines `fragvol_r` on a whole-soil volume basis. Do not conflate them.

## Exact source path

`wepppy/soils/ssurgo/ssurgo.py:526` assigns `_computeRock` output to `smr`.
Lines627–654 combine large-fragment mass fractions with the fraction of remaining
material retained by the sieve. In percent form, the expression is large-rock
percentage plus `(100-large-rock percentage)*(100-sieve10 percentage)/100`.
Lines1564–1568 emit `h.smr` as the final native horizon field, unchanged. The
alternative writer at1673 likewise emits `smr`. `fragvol_r` is fetched into
layer metadata at1097 but is not consumed by `_computeRock` or this writer.
No density conversion is needed because these source quantities already express
weight fractions. Organic/missing-sieve fallback is explicit and remains a
separate default-parameter question.

Current source SHA256 `02d3b1da89195077d32df279790314d89d19183518450ca30b9231f32390bb27`
exactly matches the retained `restriction-provenance-inputs/ssurgo.py` and its
`restriction-source-retention-v1.json` receipt. This is a source snapshot retained
by the earlier provenance audit, not proof of an independently captured source
execution at the original September soil-generation date.

## Executed emitted-input lineage

`audit_rfg_basis.py` and `rfg-audit-v1/` under the new physical-review root verify
18 generated mode histories, four selected materials and108 upper200mm native
input-horizon rows. Every emitted RFG equals its corresponding retained source
soil horizon through the normalized200mm split, in all three roles. Only known
selected materials1718465,1718494,1856573,2711184 were read. All source/input
hashes, sizes and modification times remain exact. No withheld material or dirty
`ssurgo.md` was consumed or modified.

First retained material RFG values are48%,0%,36.25%,15% respectively; underlying
horizon transitions and normalized splits remain in the numeric table. Native
computational remapping is a different stage, already recorded by initialization
observations. Original raw sieve measurements are not present in this compact
capsule; the audit does not invent a field-data recomputation or substitute current
remote SSURGO values. Field representativeness remains outside this conclusion.

The internal native capacity-basis comparison remains valid on native-interpreted
mass RFG regardless of upstream field representativeness. No input-unit repair
or global extra conversion is justified by this audit.
