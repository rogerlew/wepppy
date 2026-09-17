# Geneva first implementation performance review

Disposition: **C05 measured gates pass; C06 performance acceptance remains
open**. Keep the original 25/40-ms hit and 35-ms added-miss gates. No budget
waiver or production edit was made by QA.

## Retained evidence

- Actual service comparison: `benchmark_geneva_implementation.py`,
  `geneva_implementation_performance.json/.log`; complete exit 0, acceptance
  false. Outputs, previous generations, attempt evidence and exact ancestor/
  current module snapshots remain at
  `/wc1/batch/qa-geneva-implementation-d4842a4c6785/benchmark-manifest.json`.
- Separate diagnosis: `profile_geneva_alignment.py`,
  `geneva_alignment_component_profile.json/.log`,
  `geneva_alignment_hit_profile.txt`, `geneva_alignment_miss_profile.txt`.
  Its unique output owner is linked by the JSON manifest. Module and source
  hashes remained unchanged in both runs.

Both use only the previously audited disposable representative Geneva fixture.
There were no named project opens, source writes, HTTP calls or job submissions.
Actual services and actual freshness/publication helpers execute directly;
the owner seam supplies only `wd` and real `GenevaArtifactIO`. Source owner
lookup/HTTP/kernel orchestration remain outside this service boundary. Native
baseline modules are exact `31f77bef1` sources on the same copied inputs/output
paths, alternated against current code. Outputs are preserved before each miss.
All means refer to local warm filesystem pages, not cold storage.

## Measurements

| Boundary | Actual mean ms | Gate ms | Disposition |
| --- | ---: | ---: | --- |
| Geometry settled query hit | 26.66 | 40 | Pass |
| Geometry post-admission hit | 27.51 | 40 | Pass |
| Geometry helper-cold / actual 512-entry evicted hit | 31.42 /30.09 | 75 | Pass |
| Geometry paired settled /cold miss added | -43.60 /58.75 | 100 | Pass; negative difference is native timing variation, not a claimed speedup. |
| Burn correctly settled post-admission hit | 26.53 | 25 | Fail |
| Burn helper-cold /actual 512-entry evicted hit | 26.96 /31.59 | 40 | Pass |
| Burn paired settled miss | 88.76 current -32.36 ancestor =56.40 added | 35 added | Fail |
| Burn paired helper-cold miss | 71.15 current -26.60 ancestor =44.55 added | 35 added | Fail |

Six real 512-entry pressure preparations were completed. Correctly settled
geometry and burn post-admission hits perform zero digest payload reads, and
all measured hits avoid native generation. Generated 990-feature geometry
matches the original after removing only private provenance; aligned burn
pixels and complete rasterio profile match. Existing output modes survive
legacy admission, and actual persisted proofs are present.

### Initial phase-label error retained

The original JSON's first `burn_settled_hit` row (29.91 ms, 415,692 digest bytes
per call) was **not settled**. Geometry's eviction phase had removed burn inputs;
the harness slept before its first burn observation, then immediately measured.
The new observations were still in their one-second admission interval. This is
a benchmark preparation error, not evidence of a production settled-read defect.
Do not count that row or its zero-read gate as an implementation finding. The
subsequent correctly prepared `burn_post_admission_hit` row is valid and fails
the 25-ms mean at 26.53 ms with zero reads. Original script/JSON/log are retained.
The diagnostic run explicitly observes, waits, admits, then measures, asserting
zero reads. Future final runs must use this ordering for every independently
evicted dependency set and retain these superseded artifacts.

## Component profile and smallest follow-up

An independent correctly settled 30-call profile measured 24.90 ms, zero digest
reads; that borderline result does not override the earlier 26.53-ms failure or
the repeated miss failure. Five actual absent-target misses average 77.96 ms;
their same-operation native stacker averages 26.09 ms, leaving 51.87 ms of added
work. These ordinary timer results are separate from instrumented `cProfile`
diagnostics.

Inclusive component means overlap and must not be summed:

| Component | Settled hit | Absent-target miss |
| --- | ---: | ---: |
| Alignment input acquisition | 2 calls, 19.27 ms | 2 calls, 21.89 ms |
| Raster dependency observation | 5 calls, 15.99 ms | 4 calls, 14.41 ms |
| Initial target proof | 1 call, 3.82 ms | 1 call, 1.32 ms |
| Publication target checks | — | 2 calls, 1.42 ms |
| Attempt status publication | — | 2 calls, 13.57 ms |
| Artifact path resolution | 2 calls, 1.66 ms | 10 calls, 14.72 ms |

The profile attributes repeated raster discovery to actual companion scans,
GDAL file-list checks and profile opens. Removing publication target checks
alone cannot close the miss gap. The narrow candidate for correctness/security
review is to retain source/bound observations within one operation and use their
existing `check_unchanged()` guards at the final boundary, retaining fresh input
observation for every request, effective profile identity and selection checks.
This is a proposal, not authorization to drop post-read coherence. Repeated
artifact resolution/status cost is a secondary measured concern; confinement
and visible attempt history must remain intact.

Remeasure complete current service calls after any reviewed implementation
change. Do not subtract required guard/publication work from the existing gate.
Whole owner, HTTP/RQ, browser and archive acceptance remain separately required.
