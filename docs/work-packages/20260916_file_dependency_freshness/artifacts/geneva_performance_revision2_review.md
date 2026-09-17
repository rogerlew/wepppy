# Geneva performance revision 2

Disposition: **performance acceptance remains open; retain all four failed
mean gates**. No budget or scope was relaxed. This run evaluates the reviewed
same-call graph validation and private attempt-path optimization.

Actual evidence: `benchmark_geneva_implementation_revision2.py`,
`geneva_implementation_performance_revision2.json/.log`. The complete run exited
0 with `acceptance_passed: false`; source fixture and measured module hashes
are unchanged. Output/attempt/module retention manifest:
`/wc1/batch/qa-geneva-implementation-ce94b1a1b960/benchmark-manifest.json`.

The original failed run and its admission-label preparation error remain in
`geneva_performance_initial_failure_review.md`. This revision correctly observes
each dependency set before waiting and admitting it. **All settled hash-read
gates now pass with zero payload reads**. Six actual 512-entry eviction
preparations completed. Generated geometry, aligned burn pixels/profile,
legacy output modes and persisted proofs remain correct. Services use actual
native code, provenance and publication; exact ancestor `31f77bef1` provides
paired native controls. Owner discovery/HTTP/kernel remain outside the existing
service budget. Filesystem pages are warm; helper-cold is not cold storage.

| Boundary | Revision 2 mean ms | Gate ms | Result |
| --- | ---: | ---: | --- |
| Geometry settled /post-admission query | 28.29 /27.29 | 40 | Pass |
| Geometry cold /evicted query | 29.51 /29.99 | 75 | Pass |
| Geometry settled paired miss added | -18.38 | 100 | Pass; negative difference is timing variation. |
| Geometry cold paired miss added | 106.47 | 100 | Fail |
| Burn settled hit, 30 samples | 21.99 | 25 | Pass |
| Burn post-admission hit, 10 samples | 25.07 | 25 | Fail, narrowly |
| Burn cold /evicted hit | 26.71 /22.52 | 40 | Pass |
| Burn settled paired miss added | 51.73 | 35 | Fail |
| Burn cold paired miss added | 37.10 | 35 | Fail |

Geometry cold misses average 1006.37 ms current versus 899.90 ms ancestor.
Burn settled misses average 88.78 ms current versus 37.04 ms ancestor; cold
misses 59.52 versus 22.42 ms. Every measured hit avoids native generation and
each miss executes exactly once. These complete means include all actual
required checks and attempt publication; no component is subtracted to make
acceptance pass.

The optimization reduces burn raster observations from five to three per hit
and four to two per miss. It retains recent-change digest policy, companion
membership and joint physical/config guards within the current operation.
The remaining per-operation timings still need diagnosis: settled and cold
paired native means differ materially, and 30 settled hit samples fall from
about 28 ms initially to about 20 ms later. That variation is retained rather
than used to select a favorable subset. The separate current-code component
profile is diagnostic; it does not supersede failed acceptance gates.

## Isolated current-code diagnosis

`profile_geneva_alignment_revision2.py`,
`geneva_alignment_component_profile_revision2.json/.log` and the corresponding
hit/miss `*_profile_revision2.txt` files completed with unchanged inputs/modules.
Correctly prepared 30-call settled hits average 21.31 ms, zero payload reads.
Five absent-target misses average 62.82 ms; same-operation native stacker time
averages 24.40 ms, leaving **38.42 ms** nonnative work, still above 35 ms. This
separate diagnosis does not replace the complete paired acceptance failure.

Inclusive remaining component means (overlap; do not add): one alignment input
acquisition 9.62 ms including two raster observations totaling 6.39 ms; one
same-call final validation 2.26 ms; five ArtifactIO resolutions 5.34 ms; five
private member resolutions 5.58 ms; two attempt status publications 11.44 ms;
initial target inspection 1.10 ms and two publication target checks totaling
1.35 ms. Repeated native profile/acquisition work has been removed. The remaining
cost is distributed across required graph checks, visible attempt publication
and confined paths. Removing target checks alone cannot close the observed
settled paired miss gap. Any further optimization must preserve those contracts
and be reviewed before another acceptance run; no silent threshold increase or
favorable-sample selection is justified.
