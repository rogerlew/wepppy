# Tracker — WEPPcloud Forest Service basemap

## Quick status

**Phase**: Closed — implemented and locally validated
**Updated**: 2026-11-16
**Next milestone**: None; production deployment requires separate authorization
**Security**: High per external-egress/public-route rule; dedicated review required

## Task board

- [x] Verify live service/item/style metadata.
- [x] Correct target to WEPPpy; inspect run map, GL dashboard, and three landing-page paths.
- [x] Record explicit user requirement: Google Terrain remains default.
- [x] Revise package, discovery notes, ExecPlan, and root tracker.
- [x] Ratify canonical contract and accepted ancestor checkpoint.
- [x] Evaluate existing MapLibre reuse and prove rendering/interaction compatibility.
- [x] Implement optional basemap and landing-page credit.
- [x] Rebuild assets and pass scoped tests plus real-browser acceptance (operator requested scoped tests).
- [x] Close correctness/security reviews and promote durable rules into FSBASE-01/02/03.

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
See `artifacts/20261116_contract_decision.md`. Operator granted checkpoint commit authority with “proceed”; checkpoint committed
before production edits. Accepted ancestor revision: `277d55fba`.
Shared combined-viewer OSM compatibility is now included in acceptance.

Validation of checkpoint documents: all touched Markdown files pass scoped
`wctl doc-lint`; spelling previews reviewed; `git diff --check` passes. Existing
spelling suggestions in shared documents were left unchanged. No application
tests/builds were run because production source is unchanged. See
`artifacts/contract_reviews.md` and `artifacts/20261116_capability_audit.md`.

## Implementation validation — 2026-11-16

Frontend lint and 126 suites / 1,083 Jest tests plus 9 Node tests pass. Landing
pytest: 2 pass. Local renderer/build readback, real map/resource/hostile-input
checks, initial state, loaded coverage/zoom edges, mobile credit, authenticated
selection-box and pointer clicks, and all landing disclosures pass. No landuse
modification was submitted. FSBASE-02 addendum ancestor: `abd9f6156`.

Existing smoke suite: 6 pass, 4 skip, 4 fail. All 4 failures reproduce against
pre-change assets (9 other tests skipped in that isolation run). Security review
passes with zero findings. Full Python gate still running; final correctness
evidence confirmation and documentation closeout remain.

## Closure — 2026-11-16

Operator requested “run scoped tests”; broad run stopped after 3,171 passed and
126 skipped without failures. Final scoped checks: 327 Python, 43 map-controller
Jest, and 6 adapter Node tests pass. Both independent final reviews pass with
zero unresolved findings. All touched Markdown passes lint; served asset bytes
match generated hashes. Production deployment is excluded. Durable authority:
`docs/ui-docs/contracts/forest-service-basemap-contract.md`, including FSBASE-02
for the user-approved navigation repair.


## FSBASE-03 — fallback removal

Operator explicitly removed the legacy landing fallback, preserving both Vite
themes. Two independent contract reviews passed before ancestor `630e155e1`.
The legacy template/CDN renderer are removed. Required missing/unreadable HTML
returns a logged, plain HTTP 503. Final scoped tests and live theme validation
are retained in `artifacts/validation.md`; no production deployment.
