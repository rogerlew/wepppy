# Builder SBS support ExecPlan

## Purpose and context

Builder creates `[nodb] mods=[]` from an empty optional selection. Ron initializes
only those modules and runs0_pure.htm hides Soil Burn Severity unless Disturbed
or Baer exists. Make Disturbed an internal Builder dependency so users can
upload soil burn severity before choosing optional models. Operate in the current
branch; preserve all preexisting dirty M1 and timeout work.

## Progress

- [x] Confirm root cause and stop full-suite testing.
- [x] Prepare canonical contract and compatibility plan.
- [x] Independent contract reviews and ancestor checkpoint `f59d18942`.
- [x] Implement resolver and manifest-validation compatibility.
- [x] Validate new Builder creation and explicitly repair fair-division.
- [x] Focused tests, independent correctness review, browser evidence and closeout.

## Plan of work

After checkpoint approval, update config_builder/resolver.py effective nodb.mods
to include disturbed once, leaving user selections and capability envelope
unchanged. Update project_config_update.py selection validation for historical
and new effective lists. Check snapshot serialization and init Ron/Disturbed
with real locks. Inspect any observed parameterization dependency before broadening
scope; normal Disturbed adjustments are explicitly authorized, with no new soil versions,
lookup contents or SBS-only guard. Select the existing compatible Disturbed
mapping in registry landuse writes; preserve historical populated config mappings.
Repair fair-division persisted absent/default Landuse mapping to disturbed. Repair only
fair-division runtime controller module lists under locks and initialize absent
Disturbed state, preserving config and existing artifacts. Do not mutate a GET
or auto-migrate other projects. Exercise existing SBS upload on a disposable
new Builder run; check expected upload UI on fair-division.

## Validation and acceptance

Use wctl targeted Builder snapshot/resolver/update and route tests. Check all
exposed locales/backends in generated config. Test historical manifest reopening
and updates, malformed selection rejection, real initialized controller state,
and authenticated browser upload/classification/removal on development. Do not
run the full suite. No production installation or push.

## Surprises & Discoveries

The builder omits the controller entirely; a template-only change is insufficient.
Each NoDb controller persists its own module list, so existing-run repair must
cover event-dispatching controllers as well as Ron.

## Decision Log

2026-09-10 UTC: use the existing SBS controller and keep upload optional. Preserve
old config bytes; explicit scoped enable for the named existing run.

## Outcomes & Retrospective

Completed. Standard Disturbed is always enabled for Builder projects with
source-compatible mappings. Historical manifests remain accepted; fair-division
was repaired under locks without changing config bytes. 178 focused tests,
actual creation/upload/removal/reload and generated no-SBS soil inputs passed.
The native-upload package records final classification table/map and error
recovery validation. No full Python suite; implementation remains uncommitted.
