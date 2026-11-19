# Enforce configured map boundaries during channel delineation

**Status** Implemented and locally validated 2026-11-19 UTC. Repository-wide acceptance awaits a baseline fixture repair.

## Objective

Use `[map] boundary_check` to select channel extent admission. With a configured boundary, `intersects` is the default, `covers` requires full inclusion, and `none` skips the check. When the setting is absent or resolves to unset through the existing config parser, users can attempt delineation anywhere the existing workflow accepts an extent. Reject a disjoint extent with a message that helps the user reposition the map.

## Scope and proposed behavior

- Check the extent that the workflow will use. The ordinary map modes use the submitted bounds, the map-object mode uses its decoded extent, and Upload DEM mode uses the installed raster's geographic bounds.
- Compare against the geometry itself. A shared point qualifies under intersection. Under coverage the entire extent must be within the boundary, including its edge. The workflow uses the full extent on success.
- Apply the rule before the build-channels request changes project state, invalidates readiness or enqueues work. Apply the policy to actual batch leaf and direct channel-build extents. Base project settings-only submissions have no processing extent.
- Use the server-owned effective run config. Treat a missing, unreadable or invalid asset for a set boundary as an operator configuration error with a user-safe response.
- Cover supported configurations. The operator confirmed that `salvage_logging` is deprecated. Its missing skid-segment asset requires no restoration for this package.

## Complexity budget

Reuse the run config, extent parsing, geospatial stack and existing error delivery. Start with a shared server-side check and call it at the smallest set of points that cover the supported workflows. Establish any coverage gap with a test before expanding the implementation. The budget allows zero new dependencies, services, queues or persistent stores.

## Acceptance and evidence

- [x] For a configured boundary, a disjoint request yields actionable feedback. Prior readiness, map settings and channel artifacts survive the rejected request. Verify zero new DEM or channel work for the rejected request.
- [x] A partially overlapping extent proceeds at its full size under `intersects` and is rejected under `covers`. Test inside, overlap, disjoint, edge/corner, polygon holes and multipart geometry.
- [x] Missing and legacy unset boundaries and explicit `none` bypass asset resolution entirely. A supported config with an invalid asset produces an explicit operator error.
- [x] Cover applicable extent modes and both WBT and TOPAZ. Verify the effective extent and subsequent artifacts for the actual channel workflow and cover supported batch or direct entry points identified in discovery.
- [x] Retain the request, resolved config and reloaded map state, the DEM actually consumed, and semantic readback of fresh channel raster or vector output and the map/report result. Exercise the real asset resolver and delineation consumer using representative disposable runs. For rejection, compare preexisting artifacts and readiness and inspect the job tree.
- [x] Update the canonical contract and affected user/operator guidance. Retain independent correctness and security reviews and run the applicable regression gates before implementation closeout.

The native WBT Upload DEM path was verified locally through real RQ jobs and channel artifact readback. The full pytest run stopped on a reproduced baseline SSURGO fixture failure.

## Review and ownership

WEPPcloud maintainers own the admission behavior. The operator owns decisions about preset coverage.

Security impact is provisionally high because the authenticated RQ route would read a configured asset on request. Retain an independent security review covering path containment, supported asset locations and safe error reporting. No model parameterization change is proposed.

## References

- [Canonical contract](../../schemas/channel-delineation-map-boundary-contract.md)
- [Implementation ExecPlan](prompts/active/implementation_execplan.md)
- [Package tracker](tracker.md)
- [Validation results](artifacts/20261119_validation.md)
- [Correctness review](artifacts/20261119_correctness_review.md)
- [Security review](artifacts/20261119_security_review.md)
- [Contract-first change standard](../../standards/contract-first-change-standard.md)
- [Generated artifact validation standard](../../standards/generated-artifact-validation-standard.md)
