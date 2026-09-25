# Tracker

## Progress

- 2026-09-25 UTC: diagnosis retained; package and normative checkpoint drafted.
- 2026-09-25 UTC: both contract reviewers approved after narrowing to two soil
  lookup sites and adding lifecycle/state evidence. Ancestor checkpoint: `b63e738d0`.
- Red regression: single/MOFE `thinning_30_90` fail against old implementation.
- Minimal two-site correction implemented; artifact matrix and isolated local
  choice-feminist fork validation running.
- 2026-09-25 16:01 UTC: 198 real-artifact regressions passed (939.01 seconds);
  focused suites 123 passed. Broad suite and actual-project rebuild continue.
- 2026-09-25 16:08 UTC: supported local choice-feminist fork/rebuild PASS;
  five corrected OFEs in p10.sol and matching intermediate, 12 source NoDb hashes
  unchanged. Exact candidate and uid/gid in `artifacts/local-project-result.json`.
- 2026-09-25 UTC: broad suite stopped with 5,286 passed, 54 skipped, one
  preexisting timeout assertion failure; isolated reproduction and identical
  baseline/candidate blobs retained. Later tests were not executed.
- 2026-09-25 UTC: final archive/restore checks 3 passed; independent correctness
  and QA pass with no package findings. Code delivery/local validation closed;
  full-suite success and production recovery are not claimed.

## Decisions

- Operator authorizes any case-sensitive `thinning` prefix, not an enumerated list.
- Preserve supported mulch suffix resolution; audit generated soils directly.
- Deliver code and local evidence without deploying or modifying production runs.

## Risks and ownership

Existing derived artifacts can be reused. Operator must rebuild scenarios/soils
and rerun after deployment; this package must document rather than claim repair.
Repository maintainers own the unrelated stale 60-second timeout assertion;
the unchanged runner and accepted ADR-0072 specify 120 seconds.
