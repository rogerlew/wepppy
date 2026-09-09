# Soil source decision

## Recommendation

Retain original STATSGO THICK as the reference predictor for future M3 source
planning. Do **not** automatically substitute SSURGO or approve a partial-soil
coverage cutoff from this study. This is a recommendation to the scientific
decision owner, not production wiring or an automatic fallback policy.

The offline derivation is implemented and the real paired comparison is
complete. Evidence supports source sensitivity, not calibrated equivalence or
validation against observed debris flows. Weathered-material inclusion,
profile-endpoint censoring and tolerable missing component support remain
scientific decisions; no default depth was invented to make a run available.

## Inputs and reconstruction

The three live projects still lack `soils/` directories. Study acquisition
froze 111 map units, 390 components and 1,506 raw horizons, plus bounded original
STATSGO THICK windows. All map-unit keys resolve to Non-MLRA Soil Survey Areas;
none is a WEPP substitution. Installed 2025 spatial labels and retrieval-date
SDA tables have different vintages, recorded explicitly in the fixtures.

The 12 archived controlled 10 m outlets were reconstructed with their original
FillDepressions/D8Pointer/Watershed commands and verified against archived cell
counts. Terrain T, masks, F=0.5, coefficient durations and paired rainfall are
fixed. The `az_ponderosa` user label remains; its survey areas are in New Mexico.
Its terminal catchment is 22.9858 km2, outside the paper's 0.02–8 km2 range.
The remaining 11 outlets are within that area range; nested outlets are not
independent samples.

## Measured differences

All STATSGO windows have complete spatial support on these catchments. Strict
SSURGO valid equivalent support ranges from 0 to 99.25%; two Topanga outlets
have none. The all-recorded-layer sensitivity has 84.24–99.25% support. Neither
policy yields a complete full-catchment soil predictor at any of the 12 outlets.

Common-support means use identical spatial and fractional component weights
for the two sources. Components have no mapped within-unit locations, so this
cannot remove bias from unobserved components. The full-support comparison
retains explicit unavailable rows instead of reporting known-support means as
full-catchment estimates. Source comparison includes all three support modes.

| Common-support diagnostic | Strict soil | All recorded layers |
| --- | ---: | ---: |
| Paired outlets | 10/12 | 12/12 |
| Signed thickness difference min / median / max (cm) | -39.61 / +5.12 / +34.02 | -27.01 / -4.60 / +11.26 |
| Maximum absolute probability change, all outlets (percentage points) | 19.35 | 11.52 |
| Maximum absolute threshold change, all outlets (%) | 19.90 | 12.56 |
| Maximum absolute probability change, within-area outlets (percentage points) | 19.35 | 11.52 |
| Maximum absolute threshold change, within-area outlets (%) | 17.73 | 12.56 |
| Outside-area terminal: max probability / threshold change | 17.87 points / 19.90% | 0.29 points / 0.31% |

These are effects under the predeclared diagnostic rainfall scenarios, not
published source acceptance tolerances. The 72 comparison rows preserve
unavailable states; 924 available forward/inverse scenarios cover 15/30/60 min,
fixed 5/10/20 mm and reference 50%/75% rainfall thresholds. Threshold diagnostics
are not production defaults.

Coverage sensitivity uses the unrounded tabular support, with only 1e-12
arithmetic tolerance at exact boundaries (not Float32 raster fractions):

| Minimum support, diagnostic only | Strict soil eligible / 12 | All layers eligible / 12 |
| --- | ---: | ---: |
| 50% | 8 | 12 |
| 75% | 4 | 12 |
| 90% | 3 | 7 |
| 95% | 1 | 1 |
| 100% | 0 | 0 |

## Why material and endpoint semantics matter

The original archive's embedded SAS sums layer-bottom minus layer-top depths,
excludes WATER component attributes and renormalizes weights over nonmissing
components. It has no horizon-designation filter. That transformation does not
establish whether each original survey recorded rock layers or censored depth.

In the SSURGO panel, 79 components lack horizons; 59 strict components contain
ambiguous material (including four also containing R); one has a supplied
thickness inconsistent with endpoints. Two profiles consist of explicit R from
zero and are classified as nonsoil, separately from absent horizons. No audited
profile has a topology gap or overlap, but synthetic tests cover both and
stable-ID/range duplicates. Sum, union and deepest endpoint therefore mostly
agree here; that agreement cannot ratify a policy for alternate-depth records.

There are 157 profile endpoints at 152 cm and 58 at 203 cm. These concentrations
are evidence of recurring recorded endpoints, not proof of measured bedrock or
a license to extend missing profiles to those depths. The strong policy effect
at the New Mexico terminal demonstrates why retaining R/Cr needs explicit
scientific justification even where a particular source mean happens to agree.

## Future production readiness and decision ownership

A successful Soils build is necessary but insufficient. Future integration must
validate readable raw source tables, original spatial-key lineage, populated
components/horizons and explicit support at each full contributing catchment.
Absent, empty, custom, legacy or substituted artifacts must produce specific
unavailable reasons; no automatic acquisition or live rebuild is allowed.
The [canonical contract](../../../../wepppy/nodb/mods/postfire_debris_flow/docs/m3_soil_thickness.md)
defines offline complete/partial/unavailable semantics and source boundaries.

Before approving SSURGO, the decision owner needs an explicit material policy,
a justified incomplete-component policy and a larger independent evaluation
against the intended calibrated predictor or observed outcomes. Finer mapping,
three-site agreement in selected cases, or permissive cutoff sensitivity alone
cannot supply those decisions. This package completes the offline experiment;
production availability and scientific substitution approval remain deferred.
