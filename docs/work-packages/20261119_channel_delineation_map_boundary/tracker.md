# Channel delineation map boundary tracker

## Status

Scaffolded on 2026-11-19 at 16:01 UTC. Contract and implementation milestones are queued in the [ExecPlan](prompts/active/implementation_execplan.md).

## Tasks

- [x] Create the package, map the relevant entry points and review the tracked boundary assets.
- [x] Confirm the status of `salvage_logging` with the operator.
- [ ] Verify supported assets and coverage of effective extents, including batch runs and uploaded DEMs.
- [ ] Define and review the canonical contract, including geometry and errors.
- [ ] Implement and verify the server-side check through supported entry points.
- [ ] Retain artifact readback, regression results and independent reviews.

## Decisions

- On 2026-11-19 at 16:01 UTC, recorded the operator's rule that a set `[map] boundary` requires intersection with the requested extent. Unset values bypass the check.
- The operator confirmed `salvage_logging` is deprecated. Its stale skid-segment asset reference is outside the supported asset audit and requires no repair in this package.
- The scaffold proposes standard geometric intersection, including edge or corner contact. It also proposes an explicit configuration error when a set asset cannot be used. Capture final wording and behavior at the contract checkpoint.

## Handoff

No operator input is pending. Establish supported asset and caller coverage, then write the canonical contract before editing runtime code. Record any additional supported preset with an ambiguous boundary asset for operator review if discovered.
