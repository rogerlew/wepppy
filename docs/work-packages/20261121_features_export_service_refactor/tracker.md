# Features Export service refactor tracker

## Done

- [x] Move carrier identity mapping and cached artifact validation.
- [x] Verify the existing call paths with 231 focused tests and generated artifact readback.
- [x] Close implementation and archive its ExecPlan.

## Decisions

- **2026-11-22 05:53 UTC** — Extract two focused units. Keep path resolution
  and cache policy in the service so its callers continue to share the same
  eligibility decisions.
- **2026-11-22 05:57 UTC** — Mount the repository-pinned Markdown wheel into a disposable
  test container for the route test slice. The installed image is missing
  that wheel.

## Integration

The implementation commit is . The PR records remote check
results and merge status. The integration receipt follows the accepted commit.
