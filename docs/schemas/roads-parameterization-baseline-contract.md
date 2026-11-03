# Roads repository parameterization baseline contract

Status: current-production baseline documented 2026-11-03; no scientific default
change. Project binding and explicit overrides are specified separately in the
[settings contract](roads-settings-contract.md). This contract makes the existing
repository values and assembly rules explicit; it does not certify field calibration.

## Authority and ownership

The repository baseline consists of both the bundled source files under
`wepppy/nodb/mods/roads/legacy_templates/` and the selection/transformation rules in
`wepppy/nodb/mods/roads/roads.py`. Neither files nor Python rules alone describe the
complete parameterization. Do not make an independent numeric defaults table in
the UI or treat generated `.sol`/`.man` files as mutable project configuration.

`roads.nodb`, written through the Roads controller, owns a project's selected
baseline and overrides under the settings contract. Repository updates must not
silently rebase bound project settings. The generated native input files record
what preparation actually emitted. The native solver can further transform these
inputs; baseline input values are not necessarily instantaneous effective physics.

Disturbed's project lookup is an architectural analog, not the authority for
production Roads template values. Conditioned generated-soil research fixtures,
legacy-comparison statistics and external FSWEPP installations are not production
baseline sources. External references in older specification sections establish
historical derivation; the in-repository files listed here supply current bytes.

The [machine-readable inventory](../work-packages/20261029_roads_parameterization_program/artifacts/parameterization-baseline-inventory.json)
contains all 16 soil files, both management files, exact numbered source records,
parsed soil values, SHA256 hashes, and source-rule/native-source bindings. Its
[read-only generator](../work-packages/20261029_roads_parameterization_program/artifacts/parameterization-baseline-inventory.py)
reproduces the inventory; retain historical inventories rather than replacing them
when the baseline changes. The inventory is evidence, not another editable source.

## Selection and normalization

The existing project fallbacks are gravel surface, low traffic, loam texture and
20% profile fragments. Valid segment/mapped attributes retain their existing
precedence over fallbacks; invalid source values resolve through the documented
resolver and must retain truthful source labels. Overrides under the revised
settings contract apply deliberately after ordinary baseline resolution.

Surface aliases `graveled`, `dirt`, `native` and `unpaved` select gravel;
`asphalt` and `concrete` select paved. Texture aliases `clay loam`, `sandy loam`
and `silt loam` select clay, sand and silt. Traffic aliases `no` and `notraffic`
select none; legacy condition mappings are impassable -> none, year round -> high,
and new2011 -> low. These are categorical baseline choices, not measured continuous
surface-cover, texture or vehicle-count calibration inputs.

Template names are `3{g|p}{clay|loam|sand|silt}{suffix}.sol`:

| Execution design | Gravel suffix | Paved suffix |
| --- | --- | --- |
| Inslope rocked/vegetated ditch (`inslope_rd`) | 10 | 10 |
| Inslope bare ditch (`inslope_bd`) | 2 | 1 |
| Outslope rutted | 2 | 1 |
| Outslope unrutted execution | 2 | 1 |

The unrutted execution explicitly calls selection with `outslope_rutted` in its
profile and remainder branches. Calling the private selector directly with paved
`outslope_unrutted` would seek a missing suffix-2 file; that is not the current
production execution call. Read critical shear from file contents: paved suffix-1
road rows contain **2 Pa**, not 1 Pa. The suffix is an identifier, not a formula.

## Soil quantities and complete baseline matrix

Each source soil is version `98.4`, with three roles in order Road, Fill, Forest.
Each role's header contains soil name, texture, layer count, albedo, initial relative
saturation, Ki, Kr, critical shear and AVKE. Source horizon rows contain bottom
depth (mm), sand (%), clay (%), organic matter (%), CEC (meq/100 g), and fragment
marker. The inventory records every one of these values, not only editable fields.

In the matrix below, every role cell is **AVKE (mm/h), Ki (kg s/m4), Kr (s/m),
critical shear (Pa)** before traffic adjustment. Values are read from content.

| Source file | Road | Fill | Forest/buffer |
| --- | --- | --- | --- |
| 3gclay10.sol | 8.4, 1.5e+06, 0.0002, 10 | 7.1, 1.5e+06, 0.0002, 2 | 20, 10000, 0.0002, 2 |
| 3gclay2.sol | 8.4, 1.5e+06, 0.0002, 2 | 7.1, 1.5e+06, 0.0002, 2 | 20, 10000, 0.0002, 2 |
| 3gloam10.sol | 8.1, 2e+06, 0.0003, 10 | 11.4, 2e+06, 0.0003, 2 | 26, 120000, 0.0003, 2 |
| 3gloam2.sol | 8.1, 2e+06, 0.0003, 2 | 11.4, 2e+06, 0.0003, 2 | 26, 120000, 0.0003, 2 |
| 3gsand10.sol | 10.2, 2e+06, 0.0004, 10 | 14.3, 2e+06, 0.0004, 2 | 30, 130000, 0.0004, 2 |
| 3gsand2.sol | 10.2, 2e+06, 0.0004, 2 | 14.3, 2e+06, 0.0004, 2 | 30, 130000, 0.0004, 2 |
| 3gsilt10.sol | 8.6, 2e+06, 0.0003, 10 | 11.4, 2e+06, 0.0003, 2 | 25, 120000, 0.0003, 2 |
| 3gsilt2.sol | 8.6, 2e+06, 0.0003, 2 | 11.4, 2e+06, 0.0003, 2 | 25, 120000, 0.0003, 2 |
| 3pclay1.sol | 0.08, 5, 0.0002, 2 | 18, 1e+06, 0.0002, 1.4 | 20, 10000, 0.0002, 1.4 |
| 3pclay10.sol | 0.08, 5, 0.0002, 10 | 18, 1e+06, 0.0002, 2 | 20, 10000, 0.0002, 2 |
| 3ploam1.sol | 0.08, 5, 0.0003, 2 | 22, 2.3e+06, 0.0003, 2 | 26, 120000, 0.0002, 2 |
| 3ploam10.sol | 0.08, 5, 0.0003, 10 | 22, 2.3e+06, 0.0003, 2 | 26, 120000, 0.0002, 2 |
| 3psand1.sol | 0.08, 5, 0.0004, 2 | 26, 1.6e+06, 0.0004, 2 | 30, 130000, 0.0004, 2 |
| 3psand10.sol | 0.08, 5, 0.0004, 10 | 26, 1.6e+06, 0.0004, 2 | 30, 130000, 0.0004, 2 |
| 3psilt1.sol | 0.08, 5, 0.0003, 2 | 21, 2.3e+06, 0.0003, 2 | 25, 120000, 0.0002, 2 |
| 3psilt10.sol | 0.08, 5, 0.0003, 10 | 21, 2.3e+06, 0.0003, 2 | 25, 120000, 0.0002, 2 |

Road Ki/Kr above are high-traffic baseline values. For low **and** no traffic,
Roads divides both road coefficients by four. It does not apply this division to
fill/forest Ki/Kr and does not modify AVKE or critical shear for traffic. Thus
ordinary gravel/loam low-traffic road inputs are AVKE 8.1, Ki 500000, Kr 0.000075,
and critical shear 2; fill remains 11.4, 2000000, 0.0003, 2 and forest remains
26, 120000, 0.0003, 2. Paved road Ki 5 similarly becomes 1.25 under low/no traffic.
These are source values, not an assertion of equal delivered sediment response.

Fragment markers resolve as follows: road `urr` is 65% for gravel or 95% for paved;
fill `ufr` is `(profile_fragments_pct + 65) / 2`; forest `ubr` is the configured
profile-fragment value. The fill formula uses 65 even for paved roads. Native r7
caps input fragments at 85%; a serialized road value of 95 is therefore consumed
as 85. This is subsurface fragment mass fraction, not surface armor or cover.

Road source horizons end at 200 mm; fill and forest source horizons end at 300 mm.
All soil assembly writers invoke `ensure_200mm_boundary`: road is already compliant,
while fill/forest source horizons are split into 200/300 mm rows with identical
properties. Preserve all properties and total depth under the
[200 mm contract](soil-horizon-boundary-contract.md); do not describe the entire
three-role template normalization as a no-op.

## Management and role assembly

High and low traffic select `3inslope.man`; none selects `3inslopen.man`.
The complete plant, operation, initial-condition, surface-effect, yearly and
management schedule values are retained in the inventory's exact source records.
Both files use management version 97.3, three source OFEs and a 200-year schedule.
These are executable parameter packages; preserving only a cover percentage would
lose relevant behavior and is not an acceptable baseline snapshot.

`3inslope.man` defines ROAD, FILL and FOREST plants: sparsely vegetated road,
limited fill vegetation and forest. Its road initial condition is fallow and the
road yearly schedule selects the road surface-effect sequence (blading day 152).
`3inslopen.man` makes the road vegetated and the fill forested, changing plant values and
initial conditions while retaining the yearly scenario/surface-effect assignments. The initial residue/yearly plant indices
must be read from actual data, not inferred from description labels. No traffic
therefore changes management on more than the road, even though its soil Ki/Kr
are identical to low traffic. Canopy/residue evolve under the native management
model; they are not permanent armor.

Assembly roles refer to template scenario indices: 1 road, 2 fill, 3 forest.
Single-OFE execution selects road. Routed two-OFE selects road/forest, retaining
all three plant definitions while removing the fill initial/yearly scenarios and
remapping assignment indices. Routed three-OFE keeps road/fill/forest and copies
the management source. Routed MOFE retains source scenario definitions and assigns
them in declared order, including `(3,1,2)` and `(3,1,2,3)` for unrutted strips.
Repeated forest roles are separate physical OFEs using the same baseline scenario.
A role label must be carried through assembly; an OFE index alone cannot establish
that it is road, fill or forest across these different arrangements.

Single, two, three and general MOFE soil writers select corresponding soil rows,
apply road-only traffic scaling, replace fragment markers and normalize the 200 mm
boundary. The general MOFE writer applies the road adjustment wherever source role
1 occurs. Role-wide explicit overrides must not accidentally affect a source
hillslope soil outside this template-owned assembly or alter shared Disturbed data.

## Native interpretation and validation boundaries

Source audit uses `/workdir/wepp-forest-release-20261009/src`, with exact hashes in
the inventory. In `input.for`, the legacy 98.4 branch reads AVKE from the OFE
header and converts mm/h to m/s by dividing by 3.6e6. `tilage.for` uses positive
AVKE for primary tillage-layer conductivity and copies it to the secondary layer.
This is the baseline surface-conductivity path; deeper derived properties,
management, water state and downstream native adjustments remain relevant.

Do not apply the separate horizon-conductivity floor to AVKE in an editor merely
because both use conductivity units. They are distinct input/consumer paths.
Zero or negative AVKE bypasses its positive override in `tilage.for`. Zero or
negative Ki/Kr/critical shear invokes estimation paths in `scon.for`; it does not
mean no infiltration or no erosion. New explicit numeric overrides must be finite,
positive and remain positive/finite after serialization and native conversion.
Disable/reset is a separate state, not a zero sentinel.

`param.for` combines Ki with native adjustment factors, effective intensity and
runoff, Kr with concentrated-flow terms, and critical shear with native adjustment
factors. Increasing a baseline coefficient is not a guarantee of proportional
outlet sediment; deposition and transport can control delivery. Source inspection
alone provides no calibrated interval or universal safe large-value ceiling.
Any proposed numeric engineering limits need explicit rationale and bounded native
execution evidence; floating-point representability alone is not an assurance of
safe downstream arithmetic.

## Change control and required evidence

Changes to any source template value, selector, adjustment order/formula, source
role mapping or management assignment change the repository baseline contract.
Update this contract and its inventory, include the required
[parameterization ADR](../standards/parameterization-adr-standard.md), and bind the
new baseline identity under the project settings contract before adoption. Do not
silently rewrite saved project baselines or mutate existing prepared artifacts.

Regression evidence must cover all four textures, both surfaces, high/low/none
traffic, supported designs and single/two/three/MOFE role orders. Compare actual
emitted role headers/horizons and management scenarios/assignments to the bound
sources and declared transformations. Include the paved suffix/content distinction,
road-only quarter scaling, no-traffic management differences, source fragment
markers/native clipping and 200/300 mm split. An unused override or mismatched role
must be explicit, not counted as successful propagation.

For behavior-changing overrides, verify saved project state -> reload -> preparation
-> serialized native inputs -> native outputs -> visible role-specific values and
comparisons. Preserve source and baseline-WEPP artifacts. Unit tests alone cannot
establish runtime consumer behavior or lifecycle correctness. Native-source readback
in this inventory establishes mechanisms; it is not a new native execution result.
