# Contract decision: resolve original stream outlets

Date: 2026-11-17 UTC. Starting revision: 05e3450fa.

## Authority and discrepancy

The operator explicitly requested: "we need to find the exact outlet coordinates on the stream network provided by culvert before running the stream pruning and reconcile the contracts". This authorizes this bounded repair and its contract-first implementation. No production deployment is included.

The November 15 supplied-point intersection rule conflicts with the January developer guide: supplied road-constrained points may be off-stream; FindOutlet determines a distinct modeled outlet. The incident batch ab283192-441e-41a1-baad-6c2df0c36d31 rejected seven road-snapped points, each adjacent to a supplied stream cell. This is an intended correction to the newer canonical selection rule, not a declaration that the input is invalid.

## Normative delta and scope

Amend docs/schemas/culvert-stream-selection-contract.md and ADR-0144; reconcile docs/culvert-at-risk-integration/weppcloud-integration.spec.md and dev-package/README.md. NoDb persistence and RQ response contracts remain unchanged. Before any short-stream or Strahler pruning, resolve each watershed outlet using existing native WBT FindOutlet on the original supplied stream raster and D8 pointer. Preserve the supplied road point separately. Select the coarsest candidate retaining the resolved outlet cell and watershed stream coverage; install that same outlet for delineation rather than finding a different one after pruning.

## Compatibility and security

Use additive policy selection_basis=original_outlet_v1 for new admissions. Retained version-1 policies without this basis keep exact historical supplied-point behavior; batches without policy keep legacy behavior. Do not silently rewrite failed production batches. Original outlet records bind inputs and contain both point coordinates and resolved coordinates, CRS, cell, status and failure reason. Retain these with existing skeleton archives and immutable manifests. No queue, auth, identity, or payload-schema changes. Reject client injection of the new server artifact. Missing or altered required artifacts are errors. An unresolved watershed fails individually; malformed shared grids/files fail preparation. A fresh batch is the recovery path.

## Valid states and regression evidence

Absent policy: legacy. Old policy: retained selection semantics. New policy before preparation: resolve then prune. Ready policy: verified reuse. Empty original network or FindOutlet no-outlet: explicit per-run failed record. Populated valid network: road point may be off-stream, resolved outlet must be on original and selected networks. Missing, malformed, altered or injected records: fail explicitly. Partial/failed/preparing artifacts remain observable. Regression tests use real rasters/WBT, pruning fallback, fixed outlet propagation to cropped run coordinates, immutable resume and archive/restore. Replay the seven incident watersheds and report actual artifact evidence separately from full WEPP success (SSURGO outage is separate).

## Reviews

Two independent read-only reviews by contract_review_one and contract_review_two approved the direction after resolving unqualified legacy/seeding descriptions in the API spec and developer guide. Both requested explicit retention of existing single-cell mask inclusion for the original outlet (native incident1751 resolves one cell downstream). Added this clarification to the canonical contract. Review two requested tamper coverage for outlet coordinates with unchanged input hashes; the candidate manifest will bind the outlet-record hash. Both approvals precede implementation.

Native WBT probe on copied incident payload resolves all seven original outlets. Preserve point1751 mask/crop propagation in regression coverage. No production mutation.
