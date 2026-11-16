# Implement per-run coarse-to-fine culvert stream selection

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose

Keep large culvert watersheds computationally manageable while allowing smaller
watersheds to retain finer channels. New batches choose the coarsest allowed
network retaining their supplied culvert point and watershed coverage. Preserve
the supplied DEM/streams and all existing batch artifacts.

## Progress

- [x] Operator approved per-run descending candidate selection and performance bias.
- [x] Draft canonical contract, parameterization ADR and compatibility checkpoint.
- [x] Complete two independent contract reviews; all medium findings resolved.
- [x] Standalone reviewed contract ancestor committed as `61645e8a1`.
- [x] Implement candidate generation, per-run selection and additive receipts.
- [x] Validate real-raster regressions and focused NoDb/RQ tests: 103 passed, 1 skipped; runner/helper stubtest and test-stub checks passed.
- [x] Submit forest RQ replay covering 1040 and 2913: batch `e4eb3edf-0bba-457f-adf0-17eeb61d85b8`, parent `687e8222-37ff-4ca0-bb3c-83246c8ed960`.
- [x] Parse selected/consumed artifacts, counts, outlets and final job trees: both children and finalizer succeeded.
- [x] Independent final implementation/security review and tracker/ADR handoff; no open findings.

## Surprises & Discoveries

Study showed native four-pass1040 counts near coarse baseline, but seven other
culvert watersheds lose all channels. Three passes retains all39. Coarsening and
re-extraction are not equivalent to preserving supplied stream positions.

## Decision Log

Operator/Codex,2026-11-16: choose per-run4->3->2->1->0 for nominal1m; implement
similar resolution-dependent starts and prefer simpler networks for performance.
Concrete starts4/3/2/1/1 for1/2/4/8/10m and interpolation bins1.5/3/6m are recorded
in ADR-0144. This authorized direction supersedes the earlier boundary-only
scope restriction; it does not authorize any new service, queue, auth or source
DEM changes.

## Plan of Work

Commit only the accepted contract checkpoint/amendments/reviews as an ancestor,
leaving prior experimental source and unrelated working-tree changes unstaged.
Record its hash in tracker. Then implement to the current contract at
`docs/schemas/culvert-stream-selection-contract.md`.

Inspect `wepppy/rq/topo_utils.py`, `culvert_rq.py`, `culvert_rq_helpers.py` and
`wepppy/nodb/culverts_runner.py`. Add an internal policy-intent marker at new batch admission without changing the
HTTP/client payload contract. Extend batch preparation to preserve all binary
pass candidates and corresponding junction rasters before any child is enqueued.
Generate an additive versioned manifest without changing existing summary keys.
Per-run selection must distinguish normal candidate rejection from missing or
invalid artifacts. Record selection before making the run consume those rasters;
retain deterministic resume and legacy behavior for batches without policy markers. A present marker with missing
manifest is incomplete new preparation, never legacy.
Use existing locks/cache guards for any NoDb mutations. Do not change queue edges.

Add real GDAL/WBT raster tests to prove candidate subset semantics, point and
polygon selection, fallback ladders, explicit0 override, invalid/missing artifact
errors, legacy resume, new-policy resume, and matching generated/consumed streams
and junctions. Run `wctl run-pytest tests/rq/test_culvert_rq_helpers.py`, relevant
`tests/culverts` cases, stub checks, broad-exception gate, and doc lint. Complete
appropriate broad sanity without claiming earlier unfinished suites passed.

Prepare a fresh disposable two-point source payload retaining1040 and a native
four-pass-missed point (for example2913). Preserve rasters and source feature
properties; retain semantic/hash manifests. Apply the prior forest-only active-job,
uncached SDA pre/post-restart, identity and readiness gates. Use the registered
culvert service identity and supported API script to submit real RQ jobs. Retain
job ids and confirm1040 selects4 while the smaller watershed selects a finer
candidate. Parse raster identities, outlet/channel relationships, counts and
completion; do not infer success from parent status alone.

## Validation and Acceptance

No implementation before the ancestor checkpoint. No production rollout here.
Acceptance requires actual per-run stream/junction artifacts and successful
forest RQ workflow under real worker identity. Every fallback is visible and
preserves the supplied point; no eligible original stream is an explicit failure.
Counts are performance evidence, not permission to drop a culvert connection.

## Idempotence and Recovery

Use fresh replay UUIDs; do not mutate prior runs. Retain all candidate networks
until reviews complete. Failed new preparation must not be treated as legacy
absence of a manifest. Roll back new admissions without rewriting saved topology.

## Outcomes & Retrospective

Completed 2026-11-16 UTC. Contract checkpoint `61645e8a1`, implementation
`4266e740a`, and security-review fix `d0732a4d2` implement the approved contract.
Forest batch `e4eb3edf-0bba-457f-adf0-17eeb61d85b8` selected 4 for 1040
(783 hillslopes/313 channels) and 3 for 2913 (3/1). Both supplied points and
resolved outlets remain on the consumed candidate rasters. Both children and the
finalizer succeeded; the archive retains all selection dependencies and receipts.
Authenticated artifact readbacks and independent reviews are retained in
`artifacts/per-run-validation.md` and adjacent JSON evidence.

Broad sanity passed: 13,991 passed, 440 skipped. The full sweep started before the
small base-receipt admission fix; 30 route tests and a real HTTP 400 rejection
validated that fix separately. Focused real-WBT tests prove the four candidate
masks match repeated pruning, and stubs/docs/broad-exception checks pass.

Security review caught caller-supplied `_base/stream_selection.json` entering
new runs through base cloning. Rejecting that path closes the server-only receipt
trust boundary without changing legitimate payloads. Both correctness and
security reviews have no open findings. The original three-pass experiment is
superseded, with retained artifacts and no production changes.

The native 1 m replay supports the performance-first per-run choice. Other nominal
resolution policies remain provisional heuristics; held-out calibration and the
previous 4 m TOPAZ failure remain separate follow-ups. No production rollout is
part of this completion.

Revision 2026-11-16: recorded complete forest artifact acceptance, independent
reviews and all validation gates; retained provisional scientific limits.
