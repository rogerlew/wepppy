# Whole-soil retention: independent scientific design review

Design accepted for a finite actual-builder audit and arithmetic/domain diagnostics, not for a production conversion or native capacity candidate. No implementation, model build/run or old-root write was performed. Restrict real source acquisition to the four admitted mapunits 1718465, 1718494, 1856573 and 2711184; retain all eligible and excluded row identities and source nulls rather than expanding the panel or selecting favorable records.

## Source and transformation basis

The primary [NRCS SDM 4.3 table/column definitions](https://sdmdataaccess.nrcs.usda.gov/documents/TableColumnDescriptionsReport.pdf) describe 33 kPa and 1500 kPa retention as volumetric percentages of the whole soil. These metadata support a source-basis classification, not field accuracy or a claim that fragments contain no water. Preserve the acquired document/version/hash and the chorizon representative-field mapping. Distinguish representative, lower and upper estimates.

Current Horizon preparation divides whole-soil retention by the complement of rock mass capped at 50 percent. Native SCON instead uses a density-derived fine-earth volume fraction CPM. Under a nonporous-fragment, additive-volume approximation, inversion of whole-soil water uses a volume complement, not a mass complement. Therefore the existing heuristic is not a general physical inverse of the native rock-volume transformation. Its intentional calibration history and practical effect are separate questions; source mismatch alone does not select a validated replacement.

Let w be prepared mass fraction and rho_f/rho_r the stated bulk-fragment density pair. The volume complement is `c=(1-w)*rho_r / ((1-w)*rho_r+w*rho_f)`. Before native retention guards or fallback, the current source-to-native projection ratio is `c_native / (1-min(w,0.5))`. Keep native cap and density changes explicit in c_native. The ratio may lie on either side of unity; do not assume universal inflation or reduction. A hypothetical source-based volume inverse can cancel a later CPM only if source/native mass, density, geometry state, rounding and other transformation assumptions match.

Do not identify dbthirdbar, estimated density, emitted density and actual native BD merely because they have compatible units. Retain their measurement/estimation provenance and volume convention. NRCS's density description uses fine-material mass and a stated soil-volume measurement; any stronger source-volume interpretation must be justified, not inferred from the native variable name. Native SCON can estimate density when input is nonpositive. Fragment density 2.65 is a retained native convention, not measured lithology truth.

Source whole-soil retention may include porous-fragment/interfacial storage or a different packing/shrinkage state. A volume inverse producing an implausible fine-earth content therefore diagnoses incompatibility of the approximation as well as possible data issues; it is not proof that the source observation is invalid. Do not reinterpret profile rock as exposed surface cover.

## Actual preparation and serialization audit

Horizon invokes Rosetta even when source FC/WP are present. Separate the dependency invocation from which estimates actually populate each output. Retain direct source use, one-sided fallback, paired sanitization fallback, estimated density and emitted build notes. Source null, source zero, invalid finite value, nonfinite value and excluded horizon are different cases. In particular, the adapter accepts ordered zero retention values, whereas native SCON can treat nonpositive values as a trigger for estimation before logarithmic calculations. A successful Python ordered-pair check does not establish native round-trip preservation.

For every actual prepared/emitted horizon retain mapunit/component/horizon keys, source rock operands, source FC/WP/density, derived mass and cap status, branch notes, unrounded prepared values, exact serialized tokens and file positions. Preserve 200 mm boundary splitting and report whether one source horizon produces multiple emitted rows. Do not count split rows as independent soil measurements. Record component weighting/selection separately from horizon arithmetic, especially incomplete source composition.

The ordinary serializer rounds FC/WP to four decimals. Diagnose serialization effects against emitted values and avoid testing native admission only on preformatted Python floats. Whole-file construction, parseability and final native execution are distinct evidence levels. Complete synthetic source contexts can exercise serialization without pretending to be additional measured materials.

## Proposed finite arithmetic and admission controls

Freeze exact controls before deriving results. A compact useful grid is eight mass percentages (0, 20, 49.99, 50, 50.01, 80, 85, 90), three explicitly hypothetical fine-earth densities (0.8, 1.3, 1.8 g/cm3), and three ordered whole-volume FC/WP pairs (0.10/0.03, 0.30/0.15, 0.49/0.30): 72 arithmetic cases. These deliberately include combinations that may fail pore-volume admission; grid membership is not physical approval. Separately retain an equal-fragment-density mathematical control if desired, clearly not a feasible porous mineral soil.

Track unrounded heuristic, four-decimal emission, source-volume inverse and native-CPM-only projection independently. The 49.99/50/50.01 controls expose the adapter cap boundary; 85/90 expose native cap conditions. Native REAL boundary behavior must not be claimed from a double-only projection. No native execution is needed to label these arithmetic diagnostics.

Add explicitly named contract controls for missing FC, missing WP, missing density, source zero, unordered/negative/greater-than-one retention, nonpositive/nonfinite density, duplicate row identity, and serialization-induced equality or boundary crossing. Missing-density arithmetic should remain unavailable unless an explicitly labeled existing estimate is used; do not invent density solely to make an inverse computable. Invalid pairs must demonstrate actual existing fallback, not a mocked replacement. Tie each control to a real branch or representation boundary rather than multiplying unrelated dimensions.

## Native consumer admission priorities

1. Define each reference: whole-soil water, fine-earth water, pore volume, air-adjusted porosity, CPM and the 1500 kPa-derived dry reference. The dry reference is not automatically a universal residual-water parameter. Retain source, prepared, emitted, initialized and evolved clocks.
2. Separate SCON's air correction to porosity from CPM scaling of retention and its later SM20C/FC ratio/floor guards. Publish only diagnostics unless all guards are reproduced and independently checked. A CPM-only projection is not final native initialization.
3. Require positive finite layer support, density and relevant porosities; enforce ordered physical water limits on one explicit basis. Then separately establish downstream expression domains. Conductivity uses FC/UL inside a logarithm: both the ratio's positive domain and its singularity at one matter; a finite positive native HK on that expression requires 0<FC/UL<1. Hourly lateral drainage depends on UL-DRFC, with DRFC including air correction. Ordered dry/field/saturation alone does not protect either expression or monotonicity.
4. Preserve adjusted frozen-water coordinates: absolute liquid is ST+d(DG-FROZEN), absolute ice FRZW+dFROZEN, total ST+FRZW+dDG. Any capacity candidate must specify which store is limited, which state is written, where overflow goes and which consumer sees it next. Do not change a dry offset or capacity without conserving the corresponding absolute stock or recording an explicit flux.
5. Keep native mass caps, nonlinear guard/fallback branches, parameter updates and initial SAT handling explicit. Native initial water currently includes CPM while UL's absolute ceiling has different rock treatment; this does not authorize a blanket multiplier on all consumers.
6. Require a future ADR and complete consumer-domain/state/flux tests before runtime change. The accepted selected ET/reset explanation supplies no independent justification for a retention repair or expected annual response.

The durable contract should promote these basis/provenance/admission rules outside closed packages, while retaining unknowns and candidate prerequisites. The appropriate next decision is whether an explicitly defined conversion can be admitted for a native comparison, not whether its annual output resembles an expected answer. A bounded finding that the present heuristic is not a general volume inverse, while no replacement is yet admitted, is a complete valid outcome of this phase.

## Local source bindings

- `ssurgo.py`: `02d3b1da89195077d32df279790314d89d19183518450ca30b9231f32390bb27`.
- `scon.for`: `31f9165146283c3f64470a63f67e1a5f1e815b478a5fb638101c4fe751c76f71`.
- `watbal_hourly.for`: `c1fe46626fa9b49dea44a2116b3152a11897b42148b3c13d5bcf96fcf746ee20`.

Writer status: clear. Only this new public review artifact was written.

## Concrete declaration supersedes the optional grid proposal

The earlier 72-case arithmetic grid was a design suggestion and was not adopted or executed. The authoritative finite declaration instead has 39 acquired live horizons plus 33 synthetic controls: nine mass values (0,10,30,49.9,50,50.1,70,85,95 percent) crossed with three densities (1.0,1.3,1.6 g/cm3) at FC/WP30/10 percent, plus six semantic cases. Thus 72 is the total number of actual Horizon attempts, not 72 synthetic arithmetic cases. This concrete panel is scientifically adequate for the stated source/preparation/cap/fallback audit; it is not a broader constitutive validation grid. Eligible horizons are serialized only in the explicitly controlled single-horizon context, without a real mapunit/component-selection or native-run claim.
