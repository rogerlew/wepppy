# Contract Decision — SSURGO Intelligent Fallback M4

**Status**: Accepted checkpoint; implementation conformance pending
**Date**: 2026-07-22 UTC
**Starting implementation revision**: `b6f7599e1`
**Operator approval**: The operator directed M4/release HOLD-lift work on
2026-07-22 and previously authorized the approved ADR-0025 rollout.

## Applicable Authority

- `wepppy/soils/ssurgo/fallback.md`
- `docs/adrs/ADR-0025-ssurgo-local-vector-profile-fallback.md`
- `docs/schemas/nodb-persistence-concurrency-contract.md`
- `docs/schemas/rq-response-contract.md`
- `docs/standards/contract-first-change-standard.md`

## Normative Delta

Implement, without changing the approved fallback order, these already-ratified
requirements:

1. build/persist the 2 km candidate raster only after a residual-invalid
   dominant hillslope exists, from the configured canonical 2025 gNATSGO source;
2. use only the persisted, validated candidate raster for selection; preserve
   a global donor calculated from valid primary outcomes only;
3. accept valid current-build candidates from either primary or added
   collection, materializing only selected added donors;
4. add nullable provenance without changing existing raw/final keys or their
   semantics; and
5. reject a mutable `build-soils` request whose normalized config does not
   match the run's active config, using a canonical non-mutating 4xx response.

The native `wepppyo3` crop primitive is a supporting implementation detail. It
must crop a caller-provided canonical source to a caller-provided destination;
WEPPpy alone owns source selection and all run-path containment decisions.

## Compatibility and Security Impact

The NoDb and Parquet change is additive as specified in the package compatibility
artifact. Existing global fallback remains available for unavailable/corrupt
candidate data and failed donor materialization. A missing native categorical
dependency remains an explicit build error. Candidate source and artifact paths
are trusted/configured inputs only and remain inside their resolved roots;
atomic map/metadata publication occurs under the existing soils lock.

The RQ route gains only a pre-mutation validation check. It adds neither a route,
authorization scope, queue dependency, nor payload key. The expected error uses
the canonical RQ envelope and leaves `RedisPrep` timestamps, `Soils`, and queue
state unchanged.

## Regression Evidence Plan

- Native crop: deterministic tiny-raster bounds/copy test.
- Fallback support: resolver containment, symlink/traversal, stale metadata,
  atomic publish, and unavailable-source tests.
- Gridded build: all-valid/no-dominant no-op; primary and added eligibility;
  vector/radius/tie rules; global-only baseline; materialization rollback/retry;
  additive NoDb/Parquet propagation.
- RQ: correct config enqueues; wrong normalized config returns canonical 4xx
  without mutating controller, timestamps, or queue; discovery/defaults/job
  polling transcript for the local acceptance run.

## Independent Review and Disposition

The independent scaffold reviews recorded in the code, QA, and security
artifacts were completed before this checkpoint and dispositioned in
`2026-07-22_review_disposition.md`. A fresh independent implementation review
is required before M4 closure; its reviewers must verify this checkpoint is an
ancestor of all implementation commits.
