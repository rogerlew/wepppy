# WP12B Contract Decision

**Amendment ID**: `PC-22/WP12B-20260827-1`
**Starting revision**: `5cd18e61763430863d703d6f56454c1f00fcb2e1`
**Operator approval**: Explicit WP12B instruction in the 2026-08-27 Codex session
**Implementation conformance**: Implemented and independently reviewed Ready;
Forest acceptance pending

The operator's instruction explicitly authorizes this bounded package to compose
the climate, landuse, soil, watershed, binary-provider, template, Flask/RQ, and
project-provenance owners named below without advancing their unrelated work.
The exact matrix is limited to inventory, availability dependencies, rendering,
paired selection validation, and immutable capability provenance.

## Applicable Canonical Contracts

- `docs/schemas/project-owned-config-contract.md`, sections 5.1, 7.2, 7.2.2,
  8.2, 9, 10, and 15.
- `docs/schemas/project-owned-config-implementation-roadmap.md`, WP12B and PC-22.
- `docs/schemas/rq-response-contract.md`.
- `docs/standards/contract-first-change-standard.md`.
- `docs/standards/parameterization-adr-standard.md` and ADR-0047.

## Exact Source and Endpoint Boundary

The normative source boundary is the typed locale/component registry, domain
climate/landcover/soil catalogs, canonical WEPP binary provider, flattened
capability schema, and stable runtime maps. The paired presentation/submission
inventory includes Config Builder description/validation/create, run-page
climate catalog and dataset/station/spatial controls, Flask climate catalog and
station/mode/spatial routes, rq-engine `build-climate`, run-page landuse
mode/dataset controls, rq-engine `set-landuse-mode`, `set-landuse-db`, and
landuse build, run-page soil modes and Flask `set_soil_mode`, and Builder
watershed backend/representation/binary controls and validation.

Workers that consume already validated persisted state are in regression scope
but do not independently broaden UI authority. Existing model execution,
scientific formulas, project migration, automatic config amendment, arbitrary
mod expansion, and WP12 production deployment are excluded.

## Normative Decision

Builder uses the current validated graph. A created run uses its stored,
versioned capability graph. Schema v2 stores both axes and adjacency/allowed
tuples so independent union lists cannot authorize an invalid cross-product.
This includes representation-to-landuse-method adjacency so Multiple OFE cannot
newly select Single landuse; its existing Upload path remains supported.
Every value in the closed inventory has an explicit support disposition, and
inventory drift fails the gate.

`continental-us` keeps its stable ID and maps to exact runtime token `us`.
Locale composition is exactly one base plus zero or more compatible overlays.
No migration occurs. V1 flattened capabilities retain only their existing
coarse restrictions; missing v2 axes do not invent restrictions. A v2 authority
must be complete and fails explicitly if partial, empty, malformed, or newer
than the reader.

## Valid-State Matrix

- No `[capabilities]`: legacy locale/catalog behavior.
- Capability keys without `schema_version`: v1; enforce only present v1 axes.
- V1 missing a new WP12B axis: preserve legacy behavior for that axis.
- V1 present-empty or malformed mandatory axis: explicit configuration error;
  optional `mods` may be present-empty.
- V2 complete: axes plus stored relations are authoritative.
- V2 missing/empty/malformed mandatory axis or edge: explicit configuration
  error; do not consult the live registry or enqueue.
- Newer capability schema: degraded explicit incompatibility; no mutation.
- Persisted current value omitted from authority: render current state for
  reproducibility, disabled for reselection; ordinary build may consume it, but
  a newly submitted different unsupported value fails before mutation/enqueue.
- Legacy or v1 project update: merge-only update does not add WP12B capability
  axes because section 5.1 forbids inventing new capabilities.

## Compatibility, Security, and Rollback

The browser continues to submit stable catalog IDs where already established
and existing numeric method values at legacy endpoints. Boundary adapters map
numeric values through a domain-owned closed mapping before capability checks.
Unsupported values return the canonical field-addressable 4xx contract and
cause no NoDb write or enqueue. Stable IDs and runtime mappings are not inferred
from labels or enum order.

A v2-capable reader must deploy with v2 writing disabled before any v2 project
is created. A pre-WP12B reader is a supported rollback target only while no v2
project exists. After v2 creation, every supported rollback revision must
understand and enforce the stored v2 graph without broadening it or changing
project bytes. WP12 remains blocked until all high-security findings and Forest
evidence are closed.

## Required Evidence

The gate requires omission-detecting inventory generation, every valid graph
tuple plus invalid-edge tests, absent/v1-partial/v2-hostile/newer-schema tests,
paired presentation/submission tests with no-mutation/no-enqueue assertions,
baseline differentials before removing locale conditionals, mixed-reader
rollback proof, provider presence/health for every exposed dataset bound to the
registry and deployment revisions, and representative real execution for every
distinct provider/method family. Every Builder-exposed base and overlay receives
Forest creation evidence; there is no base-only sampling exception.

## Review Disposition

First independent correctness and governance reviews blocked the draft because
it stored only union lists, lacked a closed inventory and composition schema,
contradicted v1 compatibility, omitted checkpoint/security artifacts, and used
representative rather than advertised-provider evidence. This revision adds the
typed stored graph, exact inventory/dispositions, compatibility state matrix,
source/endpoint boundary, stable amendment identity, and complete evidence gate.
Final independent correctness, governance, and high-impact security reviews
returned **READY**. Their dispositions are recorded in this package's review
artifacts; implementation remains sequenced after the standalone checkpoint
commit.
