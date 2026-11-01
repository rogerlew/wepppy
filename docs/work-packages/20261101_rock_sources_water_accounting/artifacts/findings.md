# Source evidence and native water-accounting findings

The surface-data request now succeeds, BC's published layer definitions resolve
the previously uncertain fragment/density basis, and compiled native-expression
probes establish an additional obstacle to a simple capacity correction. This
phase changes no production parameter, native source, binary or project input.

## Surface records: available does not mean complete

The exact four-material NRCS query returned 15 rows, nine components and eight
surface-fragment records. The two reported zero representative values are real
records with nonzero upper estimates; they are distinct from absent records.

| Mapunit | Components | Fragment records | Reported component share with records | Without records | Unallocated share |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1718465 | 2 | 0 | 0% | 100% | 0% |
| 1718494 | 1 | 0 | 0% | 100% | 0% |
| 1856573 | 3 | 8 | 80% | 20% | 0% |
| 2711184 | 3 | 0 | 0% | 90% | 10% |

These shares describe survey component composition, not measured project area.
Mapunit2711184 reports only90% total composition; the reader retains10% unknown
rather than rescaling the listed components. The first reader assumed totals of
100 and failed; its script and failure disposition are retained.

The eight populated rows describe volcanic rock fragments on Cambern and
Bushvalley components, in adjacent size intervals2–75,75–250,250–600 and600–900.
Representative cover values are10/13/2/0 and20/15/1/0 percent respectively.
No row sums are promoted to total surface cover: size-class completeness,
plan-view overlap, the survey-to-run join and engineered-road applicability
remain unvalidated. Missing surface records do not establish rock-free soil.
Current records also do not reconstruct the original Roads material snapshot.

The [raw-row readback](surface-records.json), [support receipt](surface-readback.json)
and [acquisition identities](source-acquisition.json) retain these distinctions.
The source is the [NRCS Soil Data Access service](https://sdmdataaccess.sc.egov.usda.gov/webservicehelp.aspx).
A future summary producer must retain missing support and record provenance;
a scalar cover column without those fields would conceal the dominant uncertainty.

## BC SIFT: the source definition is now established

The official BC [dictionary package](https://www.env.gov.bc.ca/esd/distdata/ecosystems/Soil_Data/Soil_Data_Pkgs/SoilDataDictionaryGdb.zip)
contains SOILS_Metadata_Items entries160 and191 tied to BCSLF positions13 and44:
COFRAG describes fragment volume percentage, and BD describes fine-earth bulk
density. Entries187 and189 describe water retention on total soil volume.
These are the layer-table fields consumed by `sift.py`, rather than a generic
field-guide definition. CanSIS independently documents [COFRAG volume](https://sis.agr.gc.ca/cansis/nsdb/soil/v2/slt/cofrag.html)
and [fine-earth BD in g/cm3](https://sis.agr.gc.ca/cansis/nsdb/soil/v2/slt/bd.html).

An actual SiftHorizon serialization using a declared synthetic row with COFRAG20
and BD1.3 emits RFG20.0. The mineral density-based mass inventory instead gives
33.75796mass%, which would serialize as33.8. This confirms a dimensional defect
for inputs conforming to the published BCSLF definitions. It does not establish
what values or historical transformations exist in every deployed local copy.
The configured `/geodata/ca/env.gov.bc.ca/BC_Soil_Map.gdb/` is absent in this
workspace. No deployed BC soil was read, changed or certified.

The [serializer receipt](bc-basis-readback.json) binds the exact source and source
metadata. A subsequent bounded correction can reuse the existing conversion
helper, preserve missing sentinel handling, and test emitted/native inputs. It
still needs the reviewed parameterization ADR and generated-artifact acceptance;
this source-investigation phase does not silently alter production behavior.
Do not combine that correction with retention formulas. The [CanSIS table guide](https://sis.agr.gc.ca/cansis/nsdb/soil/v2/slt/index.html)
also cautions that layer attributes are largely modal estimates and may not
coexist in a real pedon, limiting physical interpretations of jointly assembled
properties.

## Native accounting: a smaller ceiling has additional dependencies

The [source-bound consumer map](native-water-science-review.md) traces initialization,
infiltration, percolation, drainage, extraction and fine-grid freezing/thawing.
Three distinctions matter for development:

- UL is used in response equations as well as storage limits. In particular,
  hourly lateral conductivity divides by UL-DRFC, where DRFC includes an air
  allowance above field capacity. Dry/field/saturation ordering alone cannot
  establish this denominator's validity.
- FRZW is adjusted frozen water, not total ice. A coherent coarse stock is
  ST+FRZW+THETDR*DG; liquid and ice reporting split the reference by frozen
  thickness. Fine-grid mappings contain thresholds and carried shortages,
  so coarse algebra is not proof of fine-grid conservation.
- Overflow behavior depends on FIN and time-step implementation. Active code
  routes surface return despite obsolete comments suggesting discard. Routing,
  later plant extraction and frost mapping are outside the isolated probes.

## Executed unchanged-source scalar observations

Two independent prereviews bound the declaration before compilation. Seventeen
standalone probes use exact source slices, native REAL arithmetic, a pinned
system compiler and invalid-operation traps. They are actual-source fragment
observations, not executions of complete routines or a changed model.

Nine SCON cases reproduce dry-floor adjustment and the distinction between
initial POR*CPM water and native POR-based UL. Zero-rock ceilings coincide.
Six overflow cases match independently reconstructed float32 arithmetic, with
maximum absolute signed stock-plus-surface-flux residual1.882e-9m against the
predeclared2e-8m bound. In the frozen fixture, FIN0 leaves lower-layer water above
the ice-adjusted limit; the positive-FIN branch moves about5mm upward and exports
about4mm. FIN selects the branch in this isolated block; no incoming water is
added by these slices. Daily code exports about0.000501mm of small surface excess
that hourly code retains under its existing1e-6m threshold.

The drainage control uses native UL=.4375 and yields denominator.25. Separately,
a synthetic diagnostic UL=.1875 has dry<field<effective saturation but equals
DRFC. With ST=DRFC, the exact lateral expression traps on0/0, as predeclared.
**That expected failure rejects the sufficiency of an UL-only ordering argument;
it is not an observed failure in the original histories or a successful capacity
candidate.** No native parameter was changed.

See [scalar results](scalar-readback.json), [declaration](scalar-declaration.md),
and prereviews. Full FRWATC mapping, frost transitions, HK's logarithm, and
percolation/lateral/tile/ET coupling remain unexecuted by this campaign.

## Development disposition

Source acquisition is no longer blocked by NRCS transport. It is limited by
actual missing observations and unresolved spatial/overlap meaning. BC unit
repair now has direct source support and is ready for its own reviewed,
artifact-validated implementation. Native capacity development must first
reconcile drainage thresholds/denominators and frozen reference conventions;
adding an arbitrary denominator floor would conceal the model inconsistency.

The next useful native probe is whole-routine FRWATC mapping in both directions,
with explicit fine-grid stocks, partial/full frost, liquid in frozen zones,
reference shifts and supports bracketing1mm. Declare residual ownership before
invocation. No permanent surface-rock mechanism, field calibration, full-model
capacity acceptance, Roads acceptance or production deployment follows from this
checkpoint.
