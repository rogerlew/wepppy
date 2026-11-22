# Features Export service refactor tracker

## In Progress

- [ ] Move carrier identity mapping and cached artifact validation.
- [ ] Verify the existing call paths and inspect generated artifacts with focused tests.
- [ ] Close the package and integrate its PR.

## Decisions

- **2026-11-22 05:53 UTC** — Extract two focused units. Keep path resolution
  and cache policy in the service so its callers continue to share the same
  eligibility decisions.
