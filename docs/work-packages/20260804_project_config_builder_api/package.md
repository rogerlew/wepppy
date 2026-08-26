# Project Config Builder API (WP06)

**Status**: Complete (2026-08-26)
**Initiative branch**: `feature/project-owned-config`
**Starting revision**: `e71fa16c8`
**Security impact**: high; dedicated review required

## Objective

Provide authenticated rq-engine description, validation, and synchronous
creation endpoints for the registered continental-US builder family. Creation
uses fixed token/file `config`, canonical manifest provenance, existing
idempotency/cleanup, and a strict default-off writer gate.

## Compatibility and Regression Plan

The API is additive. It accepts only typed registered component IDs, the opaque
current registry revision, and a client idempotency key. It never accepts config
tokens, filenames, paths, section names, or arbitrary options. Existing
Interfaces and preset creation are unchanged. New generated files are validated
through WP00A/WP02 and propagated into a temporary real run before Ron. Failed
validation, stale revision, forbidden override, persistence, Ron, ownership, or
idempotency completion must create no ready project and must clean only the new
run. No schema key is renamed or removed.

## Owned Requirements

PC-12: N-029, N-036, N-047, N-050, N-052 through N-054, N-091, N-095 through
N-097, R-038 through R-041, and R-044.

## Success Criteria

- [x] Description and validation return the same registry revision and resolved review.
- [x] Stale revisions return canonical 409 before allocation.
- [x] Cell-size override authorization and fixed values are enforced server-side.
- [x] Creation produces `config.cfg`, manifest, Ron state, ownership, and fixed-token location.
- [x] Replay/conflict/failure cleanup reuse WP04 semantics.
- [x] Focused, full-suite, typing, docs, correctness, and security gates pass.

## Rollout

`WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED` is strict and false when absent.
WP07 consumes the API; WP11 validates Forest; WP12 owns production enablement.

The additive OpenAPI size-budget adjustment is documented in
`docs/adrs/20260826-rq-engine-openapi-budget-builder-api.md`.
