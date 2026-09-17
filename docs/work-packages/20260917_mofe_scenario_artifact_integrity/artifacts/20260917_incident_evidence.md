# MOFE scenario artifact incident evidence

**Captured**: 2026-09-17 UTC
**Environment**: wepp1 production and local reporter attachment
**Mutation status**: read-only investigation; no production data changed

## User-Visible Incident

Abdisa reported that the Rithet Creek low-severity, moderate-severity,
prescribed-burn, and SBS scenarios appeared identical, and that the 30% and 50%
canopy-thinning scenarios also appeared identical in a hillslope response summary.
The supplied run inventory is:

| Scenario | Run ID |
| --- | --- |
| Baseline | `ventilated-gag` |
| Low severity | `equestrian-bonheur` |
| Moderate severity | `tactful-aging` |
| High severity | `incorporate-cerebrum` |
| SBS | `choice-feminist` |
| Prescribed burn | `neoliberal-dictate` |
| 30% thinning | `acetic-surprise` |
| 50% thinning | `uncrowned-bolt` |

The reporter attachment `/tmp/hillslope_response_summary.csv` has SHA-256
`042c546ee7ea9c61daf63967d2cc7ffcf4de2881739df31a95c0aa8c37bac063` and nine
lines: one header and eight scenarios. All reported metrics for low, moderate,
and prescribed burn are identical to one another. All reported metrics for 30%
and 50% thinning are identical to one another. The SBS row is slightly different,
and high severity is distinct.

## Production Artifact Evidence

The production run paths exist under `/geodata/wc1/runs/<prefix>/<runid>` on the
host and `/wc1/runs/<prefix>/<runid>` in the worker container. Relevant services
were running during the read-only inspection.

Sorted content manifests showed these equality groups across all 455 generated
MOFE management files and their prepared WEPP management files:

- baseline, low, moderate, high, SBS, and prescribed burn share the same
  `landuse/hill_*.mofe.man` manifest content fingerprint group;
- those same six runs share the same prepared `wepp/runs/*.man` manifest content
  fingerprint group;
- 30% and 50% thinning share another identical landuse management manifest group
  and another identical prepared WEPP management manifest group.

Representative effective management content confirms the hashes:

- low, moderate, and prescribed runs retain baseline forest initial canopy
  `0.90000` and interrill cover `1.00000` in representative prepared managements;
- 30% and 50% thinning both retain source-management canopy `0.40000` and
  interrill cover `0.75000` despite different stored canopy selections.

Soil inspection explains why high severity and SBS can still have different
outputs despite baseline-equivalent management files. Low, moderate, and
prescribed representative soil files differ in comments/class labels but have
the same inspected numeric values. High severity has distinct numeric soils. SBS
has a spatial mix of soil classes. This package must therefore validate landuse
and soil inputs separately instead of inferring both from the final output.

## Persisted Intent Evidence

The corresponding `landuse.nodb` records contain distinct intended state:

- low severity uses effective class `406`;
- moderate severity uses `418`;
- high severity uses `405`;
- prescribed burn uses `410`;
- SBS contains a spatial mix including `406`, `418`, and `405`;
- both thinning runs use class `424`, with `cancov_override` equal to `0.3` and
  `0.5`, respectively.

The incident is therefore a disagreement between persisted intent and generated
model artifacts, not a failure to save the visible selection.

## Confirmed Source Boundaries

### SBS values are classified twice

`SoilBurnSeverityMap.data` produces classified values 130 through 133.
`LandcoverMap.build_lcgrid()`, inherited by `SoilBurnSeverityMap`, operates over
that data and returns those classified values. In
`Landuse._build_multiple_ofe`, the result is converted to strings and looked up
again in `sbs.class_pixel_map`, which maps raw source values to classified values.
Codes 131, 132, and 133 normally miss and default to 130. The builder therefore
writes unburned managements.

Later, `Disturbed.remap_mofe_landuse` correctly treats `build_lcgrid()` output as
130 through 133 and updates persisted assignments. This ordering produces the
misleading final state: NoDb looks correct after generated files were written
incorrectly.

### Global mapping does not regenerate MOFE files

`modify_landuse_mapping_rq` updates `domlc_d` and `domlc_mofe_d`, then calls only
`landuse.build_managements()`. That method updates management summaries but does
not regenerate `landuse/hill_*.mofe.man`. Low, moderate, high, and prescribed
global remaps can therefore retain baseline files.

The selected-hillslope `Landuse.modify()` path is separate and already calls the
explicit-assignment MOFE builder. The September 11 selected-hillslope package did
not cover the global class-to-class operation implicated here.

### MOFE synthesis ignores stored canopy overrides

The MOFE segment-plan loop sets local `cancov_override` to `None` and only changes
it when RAP provides a segment-specific value. It does not initialize from
`summary.cancov_override`. Both thinning runs therefore synthesize their shared
class 424 source management at its 0.40 canopy value rather than at the stored
0.30 and 0.50 values.

## September 7 False-Positive Validation

The user cloned actual project `honorable-pin` to `aliquot-shoji` and directed an
actual-project validation. The clone build ran at approximately 2026-09-07
13:06:16 Pacific daylight time, and the user sent an email at 13:07 stating that
the MOFE issue was fixed.

Readback now shows that `aliquot-shoji/landuse.nodb` contains the intended C3S
burn classes, but all 167 generated `landuse/hill_*.mofe.man` files are
byte-for-byte identical to `honorable-pin`. The sample initial management still
contains baseline cover. Job success and correct metadata did not prove the
generated artifacts.

The closed September 7 validation artifact explicitly states that raster/SBS
grids, locks, and build scheduling were isolated with fixtures and that the tests
were not a complete live landuse or WEPP replay. Its SBS test double returned raw
values and then mapped them, unlike the real production contract. The failure to
inspect the actual cloned management files made the “fixed” conclusion invalid.

## Scope Boundary

Fix the three confirmed propagation paths and prove the complete real workflow
without changing severity rules, vegetation eligibility, scientific lookup
values, cover selections, RAP formulas, schemas, queue topology, authentication,
or deployment ownership.

## Evidence Retention Requirements

For every subsequent local, Forest, and production snapshot, retain:

- source revision and service/container identity;
- project/run provenance and job IDs;
- persisted assignment and override state;
- sorted SHA-256 content manifests for landuse, soil, prepared WEPP inputs, and
  relevant outputs;
- parsed representative and aggregate management values;
- failed and partial artifacts with status and diagnostics;
- regenerated response summaries and comparison method.

File existence, timestamps, job completion, NoDb state, or a large passing test
count cannot substitute for that evidence.
