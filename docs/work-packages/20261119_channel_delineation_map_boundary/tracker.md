# Channel delineation map boundary tracker

## Status

The scaffold is committed as `3e869bfd9`. The independent contract checkpoint is `77dbafa04`. Implementation and local native WBT validation passed. Broad regression is in progress.

## Tasks

- [x] Create the package, map the relevant entry points and review the tracked boundary assets.
- [x] Confirm the status of `salvage_logging` with the operator.
- [x] Verify supported assets and coverage of effective extents, including batch runs and uploaded DEMs.
- [x] Define and review the canonical contract, including geometry and errors.
- [x] Implement and verify the server-side check through supported entry points.
- [x] Retain artifact readback and independent correctness and security reviews.
- [ ] Record the broad regression result and close out the package.

## Decisions

- On 2026-11-19 at 16:01 UTC, recorded the operator's rule that a set `[map] boundary` requires intersection with the requested extent. Unset values bypass the check.
- The operator confirmed `salvage_logging` is deprecated. Its stale skid-segment asset reference is outside the supported asset audit and requires no repair in this package.
- The operator requested intersection and full inclusion and delegated the setting names. The contract records `none`, `intersects`, and `covers`, with intersection as the default when the boundary is configured. Edge or corner contact qualifies under intersection. An unusable required asset produces a configuration error.

## Handoff

No operator input is pending. The independent reviews cleared all medium and high findings. The [correctness review](artifacts/20261119_correctness_review.md) records the native evidence and remaining environment coverage.
