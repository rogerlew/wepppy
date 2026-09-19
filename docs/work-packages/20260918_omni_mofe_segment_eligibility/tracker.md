# Tracker

Contract checkpoint: `df504d8f6`, independent reviews dispositioned.
Implementation: segment-based selection in all three treatment branches.
Validation: 72 focused tests pass, including real combined/prepared management
readback for thinning, prescribed fire and mulch. Independent review passed.
Broad suite interrupted by the user-requested local stack restart; rerun pending.
Production: not deployed.

Release gate: actual-project Forest acceptance remains pending and is required
before release. Local regression completion does not satisfy that gate.
Local Forest stack restarted and six saved scenarios dispatched at
2026-09-18 18:51 UTC: `8c88742d-defd-4b3e-ac33-a3efd622dd42` (HTTP 202;
initial status queued). Await user completion/error notification, then inspect
generated artifacts. See `artifacts/forest_dispatch.md`.

2026-09-18 19:42 UTC disposition: low and prescribed fire failed in soil-loss
map parsing of overflow asterisks; moderate/high finished, thinning still running
at inspection. Full-model acceptance blocked. See
`artifacts/forest_failure_disposition.md`; no retry or run mutation performed.

2026-09-18 20:03 UTC: user-authorized stop and replacement batch on local Forest
using `wepp_260803`; all six scenarios submitted under
`ef226e0f-a5f7-4daf-bee6-9db5f420c7aa`. Old artifacts preserved, old thinning
jobs stopped and pending finalizers canceled. See `artifacts/forest_260803_rerun.md`.

260803 result: all six leaves plus compilation/finalization finished by
2026-09-18 21:21:41 UTC. No plot overflow; mixed-segment generated/prepared
management acceptance passes for prescribed fire and both thinning scenarios.
See `artifacts/forest_260803_results.md`. Full soil/manifests audit still running;
broad suite and matched-binary manual comparison remain pending.

Requested mixed-binary comparison complete: fire runoff differs by at most
0.130%; fire sediment is +270.5% to +378.1%. Fire-only ordering agrees, but full
ordering differs because manual thinning yields exceed manual fire yields.
See `artifacts/manual_comparison_260803.md`; no 20% sediment parity claim.

User-reported Modify Landuse channel-selection defect fixed as a selected-hillslope
contract conformance repair. Click/box/paste/submission exclude channel TOPAZ IDs;
906 frontend tests, 193 render tests, lint, bundle build and independent review
pass. See `artifacts/selection_channel_fix.md`. Not deployed to production.

Comprehensive 260803 readback subsequently finished: all six scenarios pass all
455 hillslopes with zero management/prepared-soil/serialization failures.

User's manual low-severity 260803 rerun verified: 455 hillslopes / 1065 OFEs
pass artifact readback; numeric hillslope and complete outlet summaries equal
Omni low. Across 447 byte-identical-input hillslopes versus dcc52a6, runoff
volume changes +0.003085%, sediment yield +347.86%. See
`artifacts/equestrian_260803_verification.md` for scope and attribution limits.
