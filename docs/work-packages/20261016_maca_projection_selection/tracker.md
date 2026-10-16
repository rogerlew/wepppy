# Tracker

## Progress

- 2026-10-16 UTC: Operator explicitly requested selector implementation and client patch.
- Contract, ADR and ExecPlan prepared; independent checkpoint reviews pending.
- Implementation, focused/generated-output/live checks and final review pending.

## Decisions

Preserve prior default; one combined selection from 40 pairs. Fix member identity
deterministically. Keep existing numerical and publication behavior.

## Evidence and risks

CCSM4 r6i1p1 returned all seven variables for both scenarios; initial precipitation
probe passed for the other 38 model/scenario pairs. This is bounded availability
evidence, not full-year/all-location proof. Prior broad tests stopped because a
Playwright Chromium executable was missing; account for that environment issue
when running browser validation. Production remains unchanged.
