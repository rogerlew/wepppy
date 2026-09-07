# MOFE mapping lookup tracker

**Started / updated**: 2026-09-07 19:26 UTC  
**Phase**: Validation
**Security impact**: none; dedicated review not required

## Progress

- [x] Confirm production failure and scaffold package.
- [x] Review and commit canonical contract checkpoint (38789cb4c).
- [x] Implement lookup and regression tests.
- [ ] Validate generated management outputs and required gates.
- [x] Independent correctness review: no findings.
- [ ] Full-suite outcome and package closeout.

## Decisions

2026-09-07 19:26 UTC: User explicitly requested scaffolding and execution of mapping-aware MOFE lookup after diagnosis. Preserve existing MOFE vegetation eligibility, including short grass and current flag behavior; changing burn flags is a separate behavioral decision. Production rollout is outside this package.

## Evidence

Starting revision: 83ae87a2e6c31a73866c28a4c9d63b1c7f95af29. Production MOFE keys: 106 (250), 118 (134), 120 (4), 121 (4), 105 (2). Active map c3s-disturbed requires forest 406/418/405 and shrub 421/420/419.

2026-09-07: Regression first demonstrated C3S KeyError 106 (legacy case passed); production correction then applied.

2026-09-07 19:35 UTC: 110 related tests passed, 20 skipped; final focused suite with generated cover assertions passed (18). Correctness review passed. Full repository suite running.
