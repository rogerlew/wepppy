# MOFE management artifact contract

**Status**: Accepted; local implementation validated, Forest acceptance pending.

## Scope

This contract governs three existing multiple-overland-flow-element (MOFE)
landuse generation paths:

1. soil-burn-severity (SBS) values consumed during MOFE landuse build;
2. combined MOFE management files regenerated after global class-to-class
   landuse mapping; and
3. persisted canopy-cover overrides used during MOFE management synthesis.

It corrects propagation of existing user intent. It does not add a runtime
artifact store, publication protocol, recovery system, event format, queue,
schema, service, retention policy, or scientific parameter.

## Required behavior

### SBS classification

`SoilBurnSeverityMap.build_lcgrid()` returns classified values in the `130`
through `133` namespace. The MOFE builder consumes those values directly:

- `130` remains unburned;
- `131`, `132`, and `133` select the existing effective low-, moderate-, and
  high-severity management classes; and
- nodata retains the existing unburned behavior.

The classified value must not be translated a second time through the raw-pixel
`class_pixel_map`. An explicit `domlc_mofe_override` remains final intent and
bypasses raster classification.

### Global class-to-class mapping

After the existing global mapping worker updates `domlc_d` and `domlc_mofe_d`,
it must regenerate `landuse/hill_*.mofe.man` from the final MOFE assignments by
using the existing MOFE writer before publishing its existing completion and
landuse trigger messages. It then rebuilds summaries and persists through the
existing NoDb path.

If MOFE generation, summary rebuilding, or persistence raises, the existing RQ
exception path applies and no completion or success trigger is published. This
contract does not introduce rollback, staging, retry, or partial-publication
machinery; existing locking, files, status messages, and operator diagnostics
remain authoritative.

### Canopy override

When a management summary has `cancov_override`, MOFE synthesis uses that value
as the canopy override. When no summary override exists, current source behavior
is unchanged. When RAP supplies its existing segment-specific canopy value, RAP
retains precedence over the summary override.

The existing canopy coverage mutation must regenerate MOFE managements from
the current explicit assignments before returning success. A missing assignment
map fails with build-first guidance rather than reclassifying the raster.
MOFE summary rebuilding must preserve explicit canopy overrides for retained classes,
so subsequent mapping and rebuild operations do not erase persisted selections.
These are required links in the existing thinning workflow, not new operations.

No canopy percentage, RAP formula, disturbed lookup, severity threshold, soil
parameter, or fallback value changes.

## Compatibility matrix

| State | Required result |
| --- | --- |
| Single-OFE project | Existing behavior remains unchanged. |
| MOFE assignment absent or malformed | Existing explicit failure; no success trigger. |
| SBS absent | Existing ordinary MOFE generation. |
| SBS classified as `130` or nodata | Existing unburned management. |
| SBS classified as `131`, `132`, or `133` | Apply the effective severity class once. |
| Explicit MOFE assignment override | Use the override without SBS reclassification. |
| Global mapping changes MOFE assignments | Regenerate combined MOFE files before completion. |
| Writer, summary, or persistence failure | Existing RQ exception behavior; no completion or success trigger. |
| Summary canopy override absent | Existing source/RAP behavior. |
| Summary canopy override present without RAP | Apply the stored override. |
| Summary canopy override present with RAP | Preserve existing RAP precedence. |

Later WEPP preparation continues to copy the current combined management files
through the existing workflow. Forest acceptance must verify the intended values
in both `landuse/hill_*.mofe.man` and prepared `wepp/runs/*.man`; job status or
NoDb state alone is not proof.

## Verification

### User and operator workflow

Global landuse mapping changes and canopy edits regenerate the combined MOFE
managements. After changing a scenario, prepare and run WEPP again to refresh
results; an existing report is not updated by the landuse edit alone. RAP-enabled
projects continue to use RAP's segment canopy values.

Existing affected projects need a supported rebuild and rerun after deployment.
Check selected classes and canopy in `landuse/hill_*.mofe.man`, then in prepared
`wepp/runs/*.man`, before accepting refreshed results. A failed writer can leave
partial files: retain its diagnostics and rerun the failed operation successfully
before preparing WEPP. Do not repair generated files by hand.

### Developer evidence

Regression evidence must cover classified SBS values `130` through `133`,
nodata, explicit-assignment bypass, global mapping regeneration, writer failure
without completion, 0.30 and 0.50 stored canopy overrides, absent override, RAP
precedence, single-OFE behavior, and prepared WEPP input propagation. At least
one test for each corrected producer path must parse generated management
content rather than only asserting calls or persisted metadata.

Actual-project Forest acceptance remains the release gate. Production repair is
separately blocked until the operator deploys the accepted revision and confirms
that deployment.
