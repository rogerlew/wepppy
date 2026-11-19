# Channel delineation map boundary contract decision

The implementation baseline is `1d8e078333d7f340e3a7db19e3b32ff1d8c5cfac`.
The scaffold is `3e869bfd9`.

## Authority and delta

The operator requested optional config boundary enforcement for the requested
channel extent, then asked that the work package be executed and extended to
support intersection and full inclusion. The operator delegated config value
names and confirmed that `salvage_logging` is deprecated.

This is an intentional behavior change. Use `boundary_check = none`,
`intersects`, or `covers`. Default to `intersects` with a configured boundary
to preserve the originally requested rule. Use inclusive intersection and
coverage so a shared edge qualifies under both policies when the rest of the
respective requirement holds. The explicit `none` mode allows a display
boundary without spatial admission. Existing unset boundaries preserve their
current workflow. Full inclusion is opt-in. No supported preset gets a new
explicit setting in this package.

Read the config instead of the persisted display-layer field. The Batch Runner
sets that field to a per-run target outline. Batch settings-only submissions
can save shared parameters regardless of their currently visible map because
the actual extent is selected at the leaf. Validate the leaf's processing extent.
Treat invalid settings or assets as a configuration error and reject the request.

## Applicable contracts and security

The normative rule lives in
[Channel delineation map boundary](../../../schemas/channel-delineation-map-boundary-contract.md).
The [RQ response contract](../../../schemas/rq-response-contract.md) retains its
error envelope, and the [request payload contract](../../../schemas/request-payload-contract.md)
retains existing fields. The
[controller state](../../../schemas/rq-controller-state-contract.md) and
[agent API](../../../schemas/rq-engine-agent-api-contract.md) contracts link the spatial policy. The [map behavior guide](../../../ui-docs/map-specification-and-behavior.md)
describes the user's action. WBT-specific boundary and conditioning contracts
remain independent.

The authenticated route gains a config-referenced file read. Resolve only local
static GeoJSON, check canonical path containment, and sanitize errors. The
config is resolved from the project after run authorization. No extra API
field, permission, queue, dependency or output schema is needed.

## Evidence

Exercise supported built-in assets, actual effective config reads, missing and
empty settings, legacy map state, malformed and external references, and
intersect/cover differences including holes and touching geometry. Verify
request modes, error status and preservation of prior readiness, no enqueue on
rejection, and artifact readback for a successful delineation. Verify batch
leaf checks and independence from a generated overlay.

## Independent review disposition

Two read-only reviewers completed the contract review on 2026-11-19 UTC.

- Correctness review identified the legacy string reader's treatment of
  `none` as absence, missing controller and agent API contract references, and
  the Upload DEM replacement window. The contract now defines raw policy
  semantics, links both canonical contracts, preserves existing parse errors,
  and requires the worker to recheck the authoritative extent under the
  watershed lock. Batch base settings and leaf processing are documented
  separately.
- Security review approved the design and requested explicit static-root
  ownership, symlink containment, redaction, and evidence showing
  authorization and config match precede asset access. These are incorporated
  in the contract or regression scope. Both reviewers confirmed the tracked
  active boundary geometries are valid polygons.
