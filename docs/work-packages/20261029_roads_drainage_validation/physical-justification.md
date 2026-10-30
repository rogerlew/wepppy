# Physical basis and limits of the drainage experiment

The experiment is justified as a test of a boundary-condition hypothesis. It does
not yet justify replacing the production conductivity rule. Agreement with FSWEPP
WEPP2010 is a compatibility objective, not a measured water or sediment balance.

## Primary physical evidence

Wu and Dun introduced WEPP subsurface-flow changes because excessive deep percolation
could suppress lateral runoff in shallow forest soils above restrictive bedrock.
Their recommendation supports independently measured or reliably estimated boundary
conductivity; it does not support substituting overlying soil conductivity for every
bedrock setting. This is historical motivation, not a specification of the current
binary's equation. [USDA ARS, Wu and Dun, 2005](https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/subsurface.pdf).

NRCS distinguishes a horizon's saturated conductivity from drainage of the landscape
profile: restrictive underlying material or convergent water input can maintain wet
conditions even where soil conductivity is high. Thus a high deepest-horizon value
alone cannot establish unrestricted deep drainage. The unit conversion is
1 um/s = 3.6 mm/h. [Soil Survey Manual, 2017, chapter 3, p. 222 and table 3-23](https://www.nrcs.usda.gov/sites/default/files/2022-09/The-Soil-Survey-Manual.pdf).

NRCS describes horizon Ksat as frequently estimated from soil properties rather than
directly measured. Bedrock requires separate consideration of rock type, weathering,
fractures and their connectivity, with local data preferred. These distinctions
support retaining uncertainty rather than asserting a universal soil-to-bedrock
multiplier. [National Soil Survey Handbook, amended August 2024, sections 618.55 and 618.87](https://directives.nrcs.usda.gov/sites/default/files2/1725389663/National%20Soil%20Survey%20Handbook%20%28entire%20handbook%29.pdf).
The handbook's internal cross-reference in 618.55 names 618.88, but the actual
bedrock-guide heading in the retrieved edition is 618.87.

Retrieved 2026-10-30 UTC. Source PDFs/text and SHA256 manifest are retained in
`/wc1/runs/ro/roads-drainage-validation-20261029/physical-sources/`; the portable
manifest is in `artifacts/physical-source-provenance.json`.

## Exact implemented boundary, not a literature approximation

Audit source commit `b73e93b19a724d1991d341d38a18d11e742231bd`, corresponding to the
frozen `wepp_261026`. The native source snapshots and manifest live in the v2 scratch
root's `native-source/`. `input.for:665–675` reads the format-9002 lower boundary,
converts conductivity from mm/h to m/s, and thickness from mm to m.
`watbal.for:486` / `watbal_hourly.for:570` call `purk`, which calls `perc` at line 165.

**Runtime qualification:** `main.for:163–171` sets `ui_run = 1` only when
`wepp_ui.txt` exists in the working directory. The simplified matrix and earlier
parameter studies omit it, so they use `ui_run = 0`. Production Roads copies
shared baseline files (`roads.py:3564–3581`); both source projects and the canonical
Roads fixture have this switch. The separately declared runtime bridge measures
this distinction. Do not infer production behavior from simplified runs alone.

In `perc.for:186–228`, the restricting flag chooses the lower-boundary conductivity.
For the `ui_run = 1` path, the effective conductivity is the thickness-weighted
harmonic mean of the bottom soil cell and the underlying layer:

    K_effective = (soil_cell_thickness + boundary_thickness)
                  / (soil_cell_thickness / K_soil + boundary_thickness / K_boundary)

The percolation calculation is proportional to `86400 * fx * K_effective`, capped
by available excess water. Here `fx` is the native soil-water adjustment; this
expression is not a complete independent reconstruction of the water balance.
The `ui_run = 0` branch actually used by the simplified matrix instead uses
`K_effective = 2 * K_soil * K_boundary / (K_soil + K_boundary)`; it does not use
the supplied boundary thickness in this conductivity calculation. UI mode also
changes other water-balance behavior, so a mode comparison is not an isolated
change of this equation alone. The old
exponential expression remains commented out. Consequently conductivity and layer
thickness jointly matter in UI mode; the older publication cannot substitute for this source audit.

The generated source header's restrictive layer may be an ordinary mineral horizon
selected by a Ksat threshold, not geological bedrock. The writer currently scales
its source conductivity by 1/1000 after unit conversion; when no restriction is
identified, it supplies 0.01 mm/h. See the durable
[SSURGO parameterization history](../../../wepppy/soils/ssurgo/ssurgo.md#historical-kslast-parameterization-git-record).
This study changes neither formula in production.

All study boundary thicknesses remain 10,000 mm. Using a source horizon's Ksat
across this assumed 10 m thickness is not a faithful reconstruction of that horizon's
actual thickness or deeper stratigraphy. The alternative is an interpretable
conductivity sensitivity, not a complete geological profile.

The silt source endpoint (59.8734 mm/h) comes from an emitted horizon below
WEPP's 1.8 m cap; the horizon spanning that modeled bottom has 32.4 mm/h. Therefore
this endpoint cannot be described as removing all drainage impedance at the
computational boundary. It remains the originally frozen source scenario.

The native reader also extends the last input depth and discretizes into 200 mm
cells. Keep the normalized 200 mm boundary and all depths fixed, and check the
actual WAT profile depth. There is no physical basis here for removing normalization
or changing input depth by 1 mm to cross a numerical threshold.

## Evidence attached to the soil classes

| Specimens | Source evidence | Tested source boundary | Physical interpretation |
| --- | --- | --- | --- |
| sand; new_lithic | Lithic restriction, source 0.42 and 0.035 um/s | 1.512 and 0.126 mm/h | Source-derived R-horizon alternative, not an in-situ measurement or verified effective fractured-rock conductivity |
| clay; new_lowk | Restriction selected in A2 and Bt mineral horizons, each 0.91 um/s; type N/A | 3.276 mm/h | Removes the additional bedrock-proxy scaling for a mineral horizon; thickness and underlying geology remain unverified |
| loam; holdout; silt; new_open | No identified restriction in generated provenance | Deepest emitted horizon Ksat | Soil-like continuation scenario; does not prove absence of deeper bedrock or a water table |

The conservative policy selects the source scenario only for the latter two classes;
it retains the current boundary for identified lithic cases. That retention expresses
uncertainty, not proof that the current divided-by-1000 lithic value is correct.
The source scenario is also reported for every lithic case as a diagnostic.

The old loam and holdout specimens duplicate material profiles. New profiles are
1856573 (lithic), 53949 (mineral) and 1718494 (no identified restriction). All three
are distinct from the prior material profiles, but originate from existing projects
and are not independent field-validation sites.

## Decision requirements

A candidate must be judged against every positive-reference factor-ten comparison,
zero-reference behavior, wet/dry climate strata, generated water partition, and
native accounting limits. Improvement in sediment obtained by excessive deep
percolation would repeat the problem the forest hydrology changes sought to prevent.
Neither the current rule nor the alternatives can be physically validated by these
model comparisons alone.

Before production adoption, establish whether a restriction is mineral or geological,
its depth/thickness, and an effective vertical conductivity range supported by the
source data or local evidence. Check runoff, base/lateral flow and saturation against
observations where available. Do not fit bedrock conductivity solely to legacy
sediment. Any accepted rule needs a parameterization ADR and a separate production
change with broader writer/consumer validation; this study authorizes neither.
