# MOFE management artifact contract

**Status**: Accepted. The original SBS/mapping/canopy corrections passed local,
Forest and eight-run production acceptance (2026-09-18). The later Omni
eligibility amendment has separate validation and release status below.

## Scope

This contract governs four existing multiple-overland-flow-element (MOFE)
landuse generation paths:

1. soil-burn-severity (SBS) values consumed during MOFE landuse build;
2. combined MOFE management files regenerated after global class-to-class
   landuse mapping;
3. persisted canopy and ground-cover overrides used during MOFE management synthesis; and
4. per-segment eligibility during Omni treatment selection.

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

### Ground-cover propagation

Accepted 2026-09-18; Forest conformance validated 2026-09-19. Production
deployment and existing-project repairs remain separate operator actions.

MOFE synthesis must apply saved `inrcov_override` (interrill ground cover) and
`rilcov_override` (rill ground cover) independently, after source management and
disturbed replacements. Each applies to the segment assigned that management
class; zero and one are valid fractions, and absent/None leaves source behavior
unchanged. RAP canopy precedence is unchanged; these ground overrides do not
alter canopy or its RAP calculation.

Editing either ground-cover field must regenerate combined managements from
current explicit assignments before success, just like canopy editing. Missing
or empty assignments fail with build-first guidance before the override changes;
malformed populated assignments fail through existing builder validation. Writer
failure remains visible and may leave partial files; retry successfully before
WEPP preparation. Summary rebuilding preserves all three cover overrides for
retained classes, including zero. No fields, keys, defaults, or units change.

This activates previously ignored saved ground selections on the next supported
rebuild. Deployment does not rewrite saved artifacts or reports. Operators must
inspect saved selections before rebuilding existing projects, then prepare and
rerun WEPP. Do not hand-edit generated managements. This supersedes the earlier
deliberate ground-cover exclusion: honoring explicit user selections is required
for agreement between displayed settings and executed inputs.

No canopy percentage, RAP formula, disturbed lookup, severity threshold, soil
parameter, or fallback value changes.

## Compatibility matrix

### Omni treatment eligibility (accepted 2026-09-18; implementation pending)

MOFE Omni treatment selection must inspect per-segment assignments, not reject
an entire hillslope because its dominant class is ineligible. A hillslope with
any eligible segment reaches the existing Treatments segment loop. Thinning
retains the existing exact forest/deciduous forest/mixed forest rules;
prescribed fire retains the existing forest/shrub/grass segment mapping; mulch
retains its existing nine grass/shrub/forest low/moderate/high severity fire
classes. Ineligible segments keep their
assignments. This removes the scalar gate without changing treatment parameters.
Single-OFE selection, channel exclusion and configured hillslope slope/burn
filters retain their existing behavior. MOFE missing/malformed segment state
must fail explicitly rather than silently substitute scalar assignments.
Regression evidence must parse combined and prepared managements for a mixed
hillslope whose dominant class is ineligible. Existing saved results require
an explicit rebuild/rerun; deployment alone does not refresh them.


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

Global landuse mapping changes and canopy or ground-cover edits regenerate the combined MOFE
managements. After changing a scenario, prepare and run WEPP again to refresh
results; an existing report is not updated by the landuse edit alone. RAP-enabled
projects continue to use RAP's segment canopy values.

Existing affected projects need a supported rebuild and rerun after deployment.
Check selected classes, canopy, interrill and rill cover in `landuse/hill_*.mofe.man`, then in prepared
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

Ground-cover evidence must additionally cover independent interrill/rill values,
zero/one/None, edit-triggered regeneration, summary preservation, and unchanged
RAP canopy. The artifact inventory is `landuse/hill_*.mofe.man` (generated),
`wepp/runs/p*.man` (prepared), and existing WEPP output/log files (execution and
diagnostics). Retain these using existing run browse/download and archive paths;
validate downloaded management bytes and canonical archive/restore preservation
on the disposable acceptance project. No new artifact lifecycle is introduced.
Existing synchronous coverage requests expose working state until HTTP success
or the existing error response; queued builds use existing RQ status/logs. A
failed build is not a usable completed artifact even if partial files exist.
This amendment concerns saved/direct cover overrides and retained summary
classes. Configured defaults additionally follow the section below.

### Configured cover defaults

Accepted and Forest conformance validated 2026-09-19. `set_cover_defaults`
must apply configured values to matching management classes, then regenerate
MOFE management files once from the existing per-segment assignments. Preserve
current precedence (applicable configured values replace saved overrides when
defaults are applied) and RAP canopy semantics. No default value changes.
Absent/empty defaults or no matching management classes require no regeneration.
Single-OFE behavior is unchanged. Regenerate even when saved overrides already
equal defaults so retry repairs files after a failed writer. Propagate existing
writer and invalid-assignment failures, retaining partial artifacts/diagnostics;
do not report completion or reconstruct assignments from the landcover raster.
Malformed configured values retain existing validation/error semantics.
When defaults apply in MOFE mode, absent/empty saved assignments produce the
existing build-landuse-first error before changing overrides; they must not
select the builder's raster-reconstruction path. This precheck does not apply
to no-op default cases.

Evidence covers normal initial builds and selected-hillslope modifications,
all three cover fields including zero/one, unchanged classes, single-OFE,
RAP precedence, failure/retry, prepared readback and the existing artifact
browse/download/archive inventory. This closes the stale-file gap without
changing when defaults are applied or making them absent-only fallbacks.

Actual-project Forest acceptance passed 2026-09-19. Production repair is
separately blocked until the operator deploys the accepted revision and confirms
that deployment.
