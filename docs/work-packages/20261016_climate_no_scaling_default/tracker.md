# Tracker

## Progress

- 2026-10-16 17:57 UTC: Operator approved explicit NoScaling for new projects.
- Contract and ADR prepared; both independent reviews passed after disposition
  of state-matrix and evidence-precision findings. See the review artifact.
- Checkpoint commit authorization and implementation pending.

## Decision log

Preserve configuration resolution, then replace only an unset constructor mode
with NoScaling. Do not change existing stored None or getter behavior.

## Validation

Planned: real constructor persistence/reload, configured scaling precedence,
rendered checked radio, existing EDDE output readback and focused/broad tests.
No implementation or deployment claimed.
