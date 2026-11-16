# Per-run pruning implementation validation

Contract ancestor: `61645e8a1`. Implementation: `4266e740a`; admission-review fix: `d0732a4d2`.
Host: forest. No production rollout performed.

## Topology and selection

Fresh API batch `e4eb3edf-0bba-457f-adf0-17eeb61d85b8` retained supplied
rasters and points 1040/2913. Parent job: `687e8222-37ff-4ca0-bb3c-83246c8ed960`.
The actual DEM cell size `1.0000000000089009 m` selected a starting maximum of 4.

| Point | Selected passes | Hillslopes | Channels | Selection reason |
| --- | --- | --- | --- | --- |
|1040|4|783|313|Point and watershed retain channels at the starting candidate|
|2913|3|3|1|Pass 4 misses the supplied point; pass 3 retains it|

1040 is 1.079 times the retained 726-hillslope baseline and 1.050 times the
298-channel baseline, within the twofold acceptance limit. Raster IDs and
generated watershed parquet counts agree. Both resolved outlets remain on the
consumed stream raster. Independent checks verify candidate hashes, selected VRT
source paths, exact cropped raster pixels, and outlet intersections; see
`per-run-review-artifact-readback.json` and `per-run-implementation-review.md`.

## Regression and operational evidence

Focused culvert, helper and admission tests: 103 passed, 1 opt-in live test skipped.
Real WBT tests cover 4-to-3 fallback and equivalence of all four binary candidates
to repeated WBT pruning. Runner/helper stubtest, test-stub checker, broad exception
gate and package documentation lint passed. The follow-up admission fix passed all 30 route tests and a live HTTP 400 rejection.
Authenticated manifest/receipt downloads returned HTTP 200 with exact file hashes.
The dedicated security review has no unresolved findings. The broad suite passed: 13,991 passed, 440 skipped in 4,338.64 s. It started
before the small admission fix; the 30 route tests and live rejection cover that
final change separately.

The registered culvert service identity submitted the batch without a human
account. Worker idle checks, runtime identity, rq-engine health and uncached
NRCS SDA soil construction passed before/after the forest-only targeted restart.
The superseded three-pass replay was canceled through the supported endpoint and
its data retained. Evidence files use the `per-run-` prefix; no credentials are
retained here.

## Completed runtime acceptance

Both child jobs returned success; the finalizer returned 2 successes, 0 failures,
and 0 skipped outlets. 1040 completed all 783 hillslope simulations and its
unchanged 51-year watershed simulation. Its recorded processing duration was
3,693.64 seconds; 2913 took 86.93 seconds. Cleanup/archive creation followed.

The finished archive contains all 20 required provenance, source/candidate,
receipt and run-metadata members, with exact hashes and matching receipt links.
Authenticated manifest/receipt downloads matched persisted bytes. Final archive
HTTP download and hash evidence is retained in `per-run-authenticated-archive.json`.
Independent implementation and dedicated security reviews have no open findings.

## Limits

This is native 1 m Santee runtime evidence. Resolution mapping boundaries and other
ladders have unit coverage; the 2/4/8/10 m policies remain provisional heuristics,
not a multi-site scientific calibration. Earlier 4 m terrain diagnostics retain an
unresolved TOPAZ failure. Process-level crash/lock-contention injection and a
complete restored-project execution remain outside the retained acceptance
evidence. Skeleton export preserves selection dependencies without promising a
standalone executable project.
