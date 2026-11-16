# Tracker — WEPPcloud Forest Service basemap

## Quick status

**Phase**: Contract checkpoint preparation; implementation not started  
**Updated**: 2026-11-16 18:00 UTC  
**Next milestone**: Independent reviews and checkpoint commit authority, then renderer feasibility  
**Security**: High per external-egress/public-route rule; dedicated review required

## Task board

- [x] Verify live service/item/style metadata.
- [x] Correct target to WEPPpy; inspect run map, GL dashboard, and three landing-page paths.
- [x] Record explicit user requirement: Google Terrain remains default.
- [x] Revise package, discovery notes, ExecPlan, and root tracker.
- [ ] Ratify canonical contract and accepted ancestor checkpoint.
- [ ] Evaluate existing MapLibre reuse and prove rendering/interaction compatibility.
- [ ] Implement optional basemap and landing-page credit.
- [ ] Rebuild assets; run focused/full tests and real-browser acceptance.
- [ ] Close correctness/security reviews and promote all durable rules before closure.

## Decisions — 2026-11-16 18:00 UTC

The user corrected the target to WEPPpy and explicitly requested keeping Google Terrain as default. Scope is the WEPPcloud run map and GL dashboard plus attribution on every landing-page variant. CULVERT integration findings are not evidence about WEPPpy and have been removed from the plan.

Google Terrain is a firm requirement, not an open decision. Renderer choice and precise failure UI remain evaluation/checkpoint work. Landing attribution does not change the landing map's current background provider. See package.md “Required behavior and rationale” for the behavior and its provenance.

## Risks and remaining evidence

Current run/dashboard renderers consume images, whereas this service provides styled vector data. MapLibre is already used in the separate landing stack, but cross-stack adoption, camera synchronization, interaction parity, resource loading, and performance remain unverified. Do not claim the endpoint is already integrated into WEPPpy.

## Validation

All four package Markdown files and PROJECT_TRACKER.md passed `wctl doc-lint` with zero errors/warnings. Spelling previews were reviewed; `git diff --check` passed. The canonical move tool updated inbound links, and the root entry points to the renamed package. No application tests, runtime changes, or deployment occurred.

## Handoff

Execute the active ExecPlan only when implementation is requested. Preserve unrelated dirty files, including preexisting PROJECT_TRACKER changes. Do not change branches or touch companion CULVERT repositories.


## Execution checkpoint — 2026-11-16

Starting revision: `917708c90dce46bbab920ecf9ce5f315e8611290`. Draft canonical
FSBASE-01 and linked amendments are prepared; both independent reviews pass with no unresolved findings.
See `artifacts/20261116_contract_decision.md`. Explicit standalone checkpoint
commit authority is required before production edits. Ancestor revision: pending.
Shared combined-viewer OSM compatibility is now included in acceptance.

Validation of checkpoint documents: all touched Markdown files pass scoped
`wctl doc-lint`; spelling previews reviewed; `git diff --check` passes. Existing
spelling suggestions in shared documents were left unchanged. No application
tests/builds were run because production source is unchanged. See
`artifacts/contract_reviews.md` and `artifacts/20261116_capability_audit.md`.
