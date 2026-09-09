# Peridot centroid projection correction

**Status**: Closed (2026-09-09)
**Timezone**: UTC

## Overview

Correct Peridot metadata centroid projection and vendor rebuilt binaries into WEPPpy. In seductive-sabra, the two-corner approximation reproduces all 505 stored centroids exactly but displaces them roughly 115–263 m from correctly projected pixel centers. This changes bedrock conductivity samples (for example hillslope 202 receives 0.005 instead of 0.0001).

## Scope and acceptance

Fix coordinate conversion in shared Parquet/CSV metadata writers for TOPAZ, WBT, and sub-fields. Reuse existing PROJ; preserve integer pixel indices, their existing corner-based geotransform convention, schemas, IDs, slope files, model defaults, and raster sampling policy. Validate regression fixtures and regenerated outputs from the rebuilt and vendored binaries. Commit and push both repositories on their existing branches. Live run repair and production deployment are separate operations, not part of this package.

## Compatibility and regression plan

No columns are renamed or removed. Existing saved outputs remain readable but retain incorrect geographic coordinates until regenerated. Verify non-coordinate columns and slope artifacts remain unchanged on identical input/flags. Compare new coordinates against independent pyproj transformations and demonstrate propagation to prepared WEPP soil inputs in an isolated run. The separate raster nearest-cell rounding issue is deferred.

## Fidelity and evidence

Target: faithful correction of projection, not surrogate discovery. Implementation and wiring require generated-output evidence from the rebuilt binaries. Authoritative contract: Peridot docs/contracts/watershed-output-contract.md, Centroid coordinate authority. Decision: WEPPpy docs/adrs/20260909_peridot_centroid_projection.md.

## Security triage

Security impact: none. No permissions, process boundary, queue, or authentication changes; existing binary entrypoints only. Dedicated security review not required. Correctness review is required.

## Precedent and observation

Related: 20260426_peridot_runtime_contract_hardening and 20260321_peridot_watershed_parquet_manifest. Reuse explicit writer errors and generated-artifact checks. No fallback, flag, or temporary mitigation added. Health signal: projected coordinate agreement and expected raster classes. Danger signals: unchanged approximate coordinates, changed schemas or slope files, projection failures. Observation is recurrence-triggered: verify these signals on the next operator-authorized regeneration; no live mutation occurs here.

## Stakeholders

Requesting user approves scope; Codex implements and reviews. See tracker.md and the ExecPlan for execution evidence.

## Closure — 2026-09-09 23:00 UTC

Delivered pointwise projection in all eight metadata exporters, regression coverage, three rebuilt/vendored binaries, and release/migration notes. Peridot main is pushed at 3cef07b; WEPPpy publication accompanies this closeout. Checks: 51 Rust tests passed; targeted Python 158 passed / 4 skipped; broad Python 8146 passed / 72 skipped. All three final binaries execute in the WEPPcloud container; geographic output matches pyproj and eight inspected hillslopes write 0.0001 in real MOFE soil prep.

See [validation](artifacts/validation.md), [correctness review](artifacts/20260909_correctness_review.md), and [release notes](../../dev-notes/peridot-centroid-projection.md). No production deployment or live-run repair performed. Separate follow-ups: Python sampler rounding and preexisting TOPAZ traversal nondeterminism.
