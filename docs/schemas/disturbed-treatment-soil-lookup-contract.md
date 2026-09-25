# Disturbed treatment soil lookup

Status: accepted by operator 2026-09-25; implemented and locally validated.
Production deployment and existing-run recovery remain separate.

## Class resolution

For single-OFE and multiple-overland-flow-element (MOFE) soil generation,
every case-sensitive disturbed landuse class starting with `thinning` resolves
to the existing `thinning` soil lookup row for its texture. This includes bare
`thinning`, catalog variants such as `thinning_30_90`, and custom suffixes.
Do not match an embedded substring, trim whitespace, or change case.
The original management class and class-specific artifact keys stay intact.

Existing treatment suffix resolution remains unchanged for classes that do not
start with `thinning`: `-mulch_15`, `-mulch_30`, and `-mulch_60` select the base
class's soil row. In particular, forest/shrub/grass fire severity is retained.
Bare `mulch_30` is a treatment selector, not a burned soil class, and is not
remapped to a generic soil row. Other existing suffixes retain their behavior.
None, empty strings, unknown classes, and unsupported suffixes keep their
existing resolution and downstream missing-row behavior.

## Parameters and compatibility

Apply the effective existing lookup row, including operator-edited values,
through the existing soil converter. Do not hard-code coefficients or alter
lookup schemas. For the incident's default loam row this means upper-200-mm
conductivity 40 mm/h, `kr=0.00004`, `ki=400000`, `shcrit=1`, `ksatadj=0`,
`ksatfac=1.3`, and `ksatrec=0.3`. The old missed lookup retained forest
conductivity 50 mm/h and `kr=0.00003`; MOFE 9002 supplied zero recovery metadata.

No changes to treatment eligibility, canopy/ground cover, RAP precedence,
soil formats, explicit management soil overrides, lookup-miss fallbacks,
locking, permissions, or job orchestration are authorized by this correction.
Keep the shared `lookup_disturbed_class` helper unchanged: RUSLE uses it for
custom class keys, and changing it could collapse distinct lookup rows.
Apply prefix resolution only in Disturbed's two soil-generation lookup sites;
existing PMET and Treatments behavior stays unchanged.

## Artifact acceptance and recovery

Read back actual converted soils, combined MOFE soils, and prepared
`wepp/runs/*.sol` inputs. Cover thinning prefixes and every supported mulch
level across burned vegetation/severity classes; demonstrate the old thinning
failure before the fix. A class label or job-success flag is insufficient.

Deployment does not regenerate existing artifacts. Existing generated soil
keys may be reused, so direct repeated modifier calls do not establish repair.
Use the supported soil/scenario rebuild and WEPP preparation/rerun workflow,
then inspect the consumed inputs and fresh results. Production recovery is
separate from code delivery; do not hand-edit generated soil files.

Working, failed and completed lifecycle states keep existing artifact visibility,
status, retention, browse and download behavior. Archive/restore preserves soil
bytes and relative paths; restored old results remain stale until rebuild/rerun.
Validate archive/restore byte parity locally and retain live browse/download and
fresh report checks as production release/recovery gates.

## Rationale

All thinning cover variants share the existing soil parameterization. The same
prefix rule at both soil lookup sites prevents single/MOFE drift without adding
rows for each canopy/ground-cover combination. Mulch changes management cover
while preserving burned soil parameterization; replacing it with thinning or
generic mulch values would erase fire severity. See
[ADR-0073](../adrs/ADR-0073-disturbed-thinning-soil-lookup.md).
