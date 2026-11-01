# Roads rock-cover audit

Status: bounded read-only audit. Independent review receipts accompany publication. No parameter revision or native run.

## Decision

Auditing now was justified. Do not transfer the gridded RUSLE auto estimate into Roads or replace soil RFG with surface-area cover. The present evidence supports a separate RUSLE unit-correction task and an explicit surface-cover measurement/consumer contract before any Roads cover sensitivity. The capacity consistency question remains separate.

## Actual nine-pair input evidence

All 36 retained histories were read directly: nine contrasts, legacy/generated lanes and roughness off/on. The reader binds 72 soil/management files to the accepted execution declaration. It parses 354 soil horizons and 108 initial-management OFE rows. All four histories per contrast use identical management bytes; roughness pairs retain identical soils. Every initial management scenario uses cropland format. Explicit rangeland rock-cover fields are absent; this does not establish zero surface rock.

| Contrast | Legacy road RFG (%) | Legacy fill / buffer RFG (%) | Generated first-horizon RFG, all three OFEs (%) |
|---|---:|---:|---:|
| B1 | 95 | 42.5 / 20 | 48 |
| B2 | 65 | 42.5 / 20 | 0 |
| B3 | 65 | 42.5 / 20 | 0 |
| B4 | 65 | 42.5 / 20 | 48 |
| B5 | 65 | 42.5 / 20 | 15 |
| B6 | 95 | 42.5 / 20 | 15 |
| B7 | 95 | 42.5 / 20 | 48 |
| B8 | 95 | 42.5 / 20 | 36.25 |
| B9 | 65 | 42.5 / 20 | 15 |

These are profile mass percentages, not surface-cover observations. Generated inputs retain the U12 `erosion_road_cap` conditioning. File horizons are not computational layers. The [input findings](input-findings.md) and CSVs retain role and cover details. Equal management inputs do not imply equal event-day cover, and do not exclude an absolute surface-armor omission common to both lanes.

## Native consumer evidence

All 977 recorded members of the actual reused build match their retained hashes. The [native consumer map](native-consumers.md) finds no direct RFG-to-surface-ROKCOV conversion. For these cropland inputs, protection follows generic interrill/rill/residue cover; the separate rock-specific rangeland pathway is not selected by their land-use codes. This is source-and-input branch support, not new runtime observations.

Soil RFG is capped at 85 percent during native input handling and converted to a fraction, then distributed over computational/tillage layers. Thus the table's 95 percent is an emitted input value, not a consumed 0.95 fraction. RFG affects the fine-earth volume factor CPM and also a bounded cropland consolidation coefficient feeding rill erodibility adjustment. Changing it would confound a surface-cover experiment with profile and potential erosion changes.

Generic crop cover also enters friction and infiltration and evolves through residue routines. Existing cover could already incorporate intended armor; historical intent and its faithful persistence remain unresolved. Adding rock blindly risks double counting or treating permanent rock as decomposing residue.

## Prior RUSLE estimator: useful precedent, unresolved transfer

The existing policy prefers optional SSURGO surface-cover columns, then a top-horizon profile-volume proxy, then zero. The inspected standard SSURGO summary/parquet producer does not supply those preferred columns. External/custom producers are not ruled out. None of the four expected proxy/product paths exists in the checked native history/source-case capsules; original watershed availability and RUSLE activation remain unknown. Missing observations are not zero rock.

Actual-function tests reproduce a current C-estimator units defect: raw SoilGrids values [20,80] produce a surface proxy of 0.5, where unit conversion gives 0.05. Raw 100 gives 1.0 while 101 gives about 0.101. The K path converts the recognized SoilGrids source consistently. These are synthetic arithmetic controls with injected raster I/O, not end-to-end raster execution or an explanation of Roads discrepancies. The [official SoilGrids units](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html) require dividing cfvo by ten to obtain volume percent.

The scalar normalization also redistributes cover: total proxy 0.2 and bare fractions [0.2,0.8] imply a shared fraction-of-bare control 0.4 and local added cover [0.08,0.32]. Mean preservation does not preserve spatial association or establish road/fill/buffer cover. See [proxy findings](proxy-findings.md).

## Scientific limits

The [RUSLE2 user guide, section 7.7](https://www.ars.usda.gov/ARSUserFiles/60600505/RUSLE/RUSLE2_User_Ref_Guide.pdf) treats surface rock as ground protection with overlap and recommends site-specific measurement. It cautions that soil-survey rock quantities differ in definition. Profile volume and surface area therefore remain distinct even after units are corrected.

Dividing a total-area rock estimate by bare fraction is a denominator conversion only if that estimate represents exposed rock within the same bare fraction. It is not proof of the overlap assumption. Rock beneath litter, particle-size definitions and RAP/SBS classification support need explicit treatment. RUSLE's accepted convenience prior is not field validation or a native WEPP parameter equivalence.

No sediment improvement, annual causality, field armor estimate, revised default or release adoption is claimed. Full-program baseline remains 713/766 meaningful and 31/74 small passes. Withheld materials and the human UI gate remain intact.
