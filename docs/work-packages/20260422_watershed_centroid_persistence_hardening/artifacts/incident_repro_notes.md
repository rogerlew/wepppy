# Incident Repro Notes

- Historical incident context: run `immodest-quick` had abstraction artifacts present while persisted `watershed.nodb` centroid was missing.
- This execution did not replay production run data directly; regression coverage was implemented with deterministic unit tests for:
  - centroid repair from artifacts,
  - typed failure when artifacts are unavailable,
  - stale-write rejection,
  - post-`abstract_watershed_rq` durability verification.
