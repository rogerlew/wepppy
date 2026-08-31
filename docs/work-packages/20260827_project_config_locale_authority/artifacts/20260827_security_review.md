# WP12B Security Review

**Status**: Ready
**Amendment**: `PC-22/WP12B-20260827-1`
**Security impact**: high

## Assets and Boundaries

WP12B controls which datasets, methods, binaries, and backends a run may newly
select. The risk-bearing boundaries are registry/provider ingestion, immutable
flattened capability authority, browser rendering and payloads, Flask/rq-engine
validation, NoDb mutation, and enqueue decisions.

## Required Controls

- Registry/provider input is closed, validated, revision-bound, and fails
  atomically on unknown or undispositioned values.
- Stable IDs map through closed domain-owned mappings; labels, paths, query
  values, and enum ordering never create authority.
- V2 capability graphs fail closed when partial, empty, malformed, contradictory,
  cyclic, or newer than the reader.
- Hidden/unsupported new submissions fail before NoDb mutation or enqueue.
- Existing authentication, authorization, CSRF, CAP, locking, and canonical RQ
  error contracts remain unchanged.
- Existing project artifacts are not migrated or amended on read.
- Provider and Forest evidence is bound to exact registry, deployment, and
  executable/dataset revisions.

## First Independent Review

The first review blocked implementation with four findings:

- **SEC-01 (high)**: a pre-v2 rollback reader could ignore stored graph edges
  and reauthorize invalid cross-products.
- **SEC-02 (medium)**: v2 lacked exact default/mod serialization, completeness
  invariants, unknown-key rejection, and size limits.
- **SEC-03 (medium)**: authentication/CSRF/CAP ordering was not bound to an
  exact route/method/principal matrix.
- **SEC-04 (medium)**: non-binary provider identities were underspecified.

## Disposition

- SEC-01: the contract now requires reader-first deployment with v2 writing
  disabled. Pre-v2 rollback is retired before any v2 creation; every supported
  later rollback revision must enforce v2 without broadening or writing.
- SEC-02: schema v2 now defines per-source default sections, mod edge grammar,
  exhaustive relation/default/tuple invariants, unknown/orphan rejection, ID/
  list/serialized-size bounds, and a hostile-state matrix.
- SEC-03: `20260827_endpoint_surface_matrix.md` enumerates route, method,
  transport, principal, and control order. Direct negative tests cover every
  changed boundary.
- SEC-04: the canonical contract and inventory define deterministic definition
  and deployment identities for DEM, climate, soil, landcover, and WEPP binary
  providers and bind them to registry/manifest/Forest revisions.

## Review Result

The independent security reviewer returned **READY** after confirming the
reader-first rollback gate, closed v2 graph grammar and limits, exact endpoint
access/control ordering, and deterministic provider identities. No high or
medium findings remain. The preserved undecorated climate GET behavior is
explicit residual risk and receives no new mutation authority.

## Implementation Re-review

The independent implementation security review initially retained two medium
findings. Stored schema-v2 validation still consulted live locale/climate
catalogs, and malformed authority on `set-landuse-mode` and `set-landuse-db`
fell through to generic 500 responses.

Both are closed. Historical graph validation now uses immutable schema-v2
rules and has a regression that forbids live-catalog access. Both landuse
mutation routes validate authority before mutation and return diagnostic
`409 capability_authority_invalid` responses with `details=str(exc)`; paired
tests assert no mutation. The reviewer returned **READY** with no residual high
or medium findings after 97 focused tests passed.
