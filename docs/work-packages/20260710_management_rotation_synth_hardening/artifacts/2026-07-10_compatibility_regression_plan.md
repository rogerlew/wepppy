# Compatibility and Regression Plan

Read this plan before editing management synthesis code.

## Generated Artifact Contract

The repair changes newly generated AgFields `.man` files by retaining one copy
of each structurally identical reusable scenario and remapping references to its
one-based index. It does not rename public columns or NoDb keys and does not
rewrite historical artifacts.

Compatibility rules:

- Preserve `sim_years`, management-loop year count, OFE count, and crop order.
- Preserve every model-data value and operation date in referenced scenarios.
- Treat only top-level scenario names and graph pointers as non-semantic for
  structural comparison; descriptions remain part of identity.
- Canonicalize plants, operations, initial conditions, contours, and drains.
- Never canonicalize surfaces or yearly scenarios because boundary merging may
  mutate them for one simulation year.
- Remap every `ScenarioReference` by its declared `SectionType`.
- Fail explicitly when more than 20 distinct plant scenarios remain.

## Regression Coverage

- Exact canola-plus-16-oats schedule from p3733: 17 years, bounded `ncrop`,
  structural reuse, resolvable references, and write/read round-trip.
- More than 20 distinct plant definitions: actionable pre-write failure and no
  partial destination file.
- Existing two-segment setup-year merge: retained years and merged operations.
- Existing end-to-end mode: section append and prefix behavior unchanged.
- Generated-output smoke: repaired management accepted by the current WEPP
  hillslope binary with source-project slope, soil, and climate support copied or
  referenced read-only from a temporary run.

## Rollback

Reverting the synthesizer patch restores historical generated naming/counts but
also restores the deterministic WEPP overflow. No stored data migration or
artifact rollback is needed. Historical inputs remain readable in either state.
