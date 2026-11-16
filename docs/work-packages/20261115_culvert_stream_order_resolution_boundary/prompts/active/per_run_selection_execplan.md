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
- [ ] Obtain commit authority and create standalone contract ancestor.
- [ ] Implement candidate generation, per-run selection and additive receipts.
- [ ] Validate real-raster regressions and focused NoDb/RQ tests.
- [ ] Submit forest RQ replay covering1040 and a small fallback watershed.
- [ ] Parse selected/consumed artifacts, counts, outlets and final job trees.
- [ ] Independent final review and tracker/ADR handoff.

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

Checkpoint preparation in progress; new per-run implementation not started.
