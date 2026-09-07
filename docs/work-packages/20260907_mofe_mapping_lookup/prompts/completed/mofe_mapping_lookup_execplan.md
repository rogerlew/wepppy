# Make MOFE burn management lookup mapping-aware


This living ExecPlan follows docs/prompt_templates/codex_exec_plans.md.

## Purpose / Big Picture


Multiple overland-flow elements (MOFE) divide each hillslope into segments. Burn remapping must assign each segment a management identifier from its active landuse map so C3S runs can complete landuse building.

## Progress


- [x] (2026-09-07 19:26 UTC) Diagnose failure and scaffold package.
- [x] Complete reviewed contract ancestor checkpoint (38789cb4c).
- [x] Implement and test map-aware remapping (18 focused tests passed).
- [x] (2026-09-07 19:45 UTC) Verify generated management artifacts, broad gates, and independent correctness.
- [x] (2026-09-07 19:45 UTC) Record outcomes and archive plan.

## Surprises & Discoveries


The ordinary hillslope remapper already uses get_disturbed_key_lookup; the MOFE remapper hardcodes disturbed.json IDs. C3S uses 406/418/405 for forest instead of 106/118/105.

## Decision Log


2026-09-07 19:26 UTC, Codex: use existing get_disturbed_key_lookup, preserving vegetation eligibility and rebuild timing. Operator authorized mapping-aware lookup explicitly. No burn flag or severity heuristic changes are included.

## Outcomes & Retrospective


Implemented in 1ea4b8d52 after contract ancestor 38789cb4c. The C3S regression failed on key 106 before the correction and now passes. All 18 focused tests and 110 related tests pass (20 related skips). Generated 12-segment management stacks preserve source cover values through two-year expansion and wepp/runs readback. Independent correctness review passed. Full repository validation passed: 7662 passed, 72 skipped in 780.99 seconds. Production deployment and recovery remain separate. The package is complete locally; no implementation deviations were required.

## Context and Orientation


wepppy/nodb/mods/disturbed/disturbed.py contains remap_mofe_landuse and get_disturbed_key_lookup. The latter obtains the effective map through Landuse.get_mapping_dict, including custom maps. tests/nodb/mods/disturbed/test_landuse_remap.py contains remap test fixtures. docs/schemas/disturbed-mofe-mapping-contract.md specifies the approved behavior; the NoDb persistence contract remains applicable.

## Plan of Work


Milestone 1: create the canonical contract and decision artifact, obtain two independent read-only reviews, and commit documentation before implementation. Record the ancestor revision in tracker.md.

Milestone 2: in remap_mofe_landuse, obtain the existing semantic key lookup after the no-SBS early return and replace only the forest/shrub/grass hardcoded target IDs. Test actual disturbed and C3S maps plus a custom map. Preserve current eligible vegetation classes and existing immediate/deferred management rebuild semantics.

Milestone 3: prove target summaries resolve and serialize management files under temporary wepp/runs directories. Run focused disturbed tests, related MOFE tests, broad pytest, broad-exception enforcement, and documentation lint. Obtain independent correctness review, resolve findings, update package/tracker/root board, and archive this plan.

## Concrete Steps


From /home/workdir/wepppy use wctl run-pytest tests/nodb/mods/disturbed/test_landuse_remap.py first, then wctl run-pytest tests/nodb/mods/disturbed tests/nodb/test_landuse_mofe_disturbed_scalar_lookup.py --maxfail=1. Run wctl run-pytest tests --maxfail=1 before handoff. Run wctl doc-lint --path on changed docs. Capture exact results in artifacts/2026-09-07_validation.md.

## Validation and Acceptance


C3S severity 131/132/133 yields forest 406/418/405, shrub 421/420/419, grass 431/430/429. Legacy disturbed yields unchanged identifiers. Custom semantic keys must resolve through the real lookup. No SBS must remain a no-op even with no usable mapping. Empty OFE assignments with a complete map stay empty. Incomplete required semantic maps fail explicitly before assignment mutation. Generated management text must agree with the selected target summary. Rebuild timing must remain covered.

## Idempotence and Recovery


Tests write only temporary data. No production run files are edited. A failed production run should be rebuilt from baseline after deployment; rerunning only the remapper on already-burned assignments is not a recovery procedure. No new schema keys, dependencies, or fallback wrappers are introduced.

## Artifacts and Notes


Incident: wepp1, aliquot-shoji, job 041e93ae-3103-4bb4-b4dc-f00471a87d30, ended 2026-09-07 16:50:40 UTC. See package.md for failure counts and compatibility plan.

## Interfaces and Dependencies


Keep remap_mofe_landuse(*, rebuild_managements: bool = True) unchanged. Reuse get_disturbed_key_lookup() -> Dict[str, str], existing map loaders, management serializers, and existing NoDb locking.

Revision note: initial plan records the narrow operator-approved correction and separates production rollout.

Revision note (2026-09-07 19:39 UTC): recorded implementation, regression, generated-output evidence, and independent review; full-suite closeout remains pending.

Revision note (2026-09-07 19:45 UTC): closed all milestones after full-suite success; archive this completed execution record.
