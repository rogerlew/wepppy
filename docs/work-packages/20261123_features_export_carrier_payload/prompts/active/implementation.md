# Consolidate carrier payload preparation

## Purpose / Big Picture

Keep a single ordered sequence for output column selection, unit conversion,
optional temporal reshaping and identity normalization in
`wepppy/nodb/mods/features_export/service.py`. A CSV or Parquet request must
still bypass geometry access. Spatial exports must retain geometry attachment,
event placeholders, requested projection and serialization.

## Progress

- [x] 2026-11-24 UTC. Identify the shared sequence and its format-specific boundaries.
- [ ] Refactor the builder and update the service internals guide.
- [ ] Validate the payloads and record the local test results.

## Surprises & Discoveries

The preceding extraction left this builder as the longest function in the service.

## Decision Log

2026-11-24 UTC. Keep a single service implementation and use existing materializers,
contracts and writers. Tabular identity backfill follows output naming. Geometry
attachment precedes it for spatial outputs.

## Validation and integration

Run the existing Features Export NoDb, RQ and route tests from the candidate.
Inspect generated GeoPackage contents and tabular values using the fixture
tests. Attempt the repository-wide pytest gate. Commit the scoped changes and
merge through the local master worktree.

## Outcomes & Retrospective

Pending validation.
