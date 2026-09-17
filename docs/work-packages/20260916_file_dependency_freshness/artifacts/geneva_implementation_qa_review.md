# C05/C06 final implementation QA

**Scoped quality and amended performance acceptance: PASS.** All 16 gates pass
in a fresh actual-service run after canonical amendment checkpoint `21aacd74f`.
Original failed runs remain failed and retained. Full owner/HTTP/RQ/browser and
cross-wave runtime acceptance are separate; this review does not mark the
package complete.

## Measured complete behavior

`benchmark_geneva_implementation_amended.py` and
`geneva_implementation_performance_amended.json/.log` retain every sample,
module hash and amendment identity. Large inputs, previous outputs, attempt
records and source snapshots remain at
`/wc1/batch/qa-geneva-implementation-3276153dea74/benchmark-manifest.json`.
The completed run reports unchanged copied inputs and production module hashes.
It uses UID 1000/GID 993, real `GenevaArtifactIO` and native services on disposable
inputs, with exact ancestor `31f77bef1` controls. There are no named project
opens, live HTTP requests, queue submissions or model-kernel execution.

| Complete service boundary | Mean ms | Amended gate ms |
| --- | ---: | ---: |
| Geometry settled /post-admission hit | 27.85 /30.34 | 40 |
| Geometry helper-cold /actually evicted hit | 37.12 /29.14 | 75 |
| Geometry settled /cold miss added | -8.40 /86.33 | 125 |
| Burn settled /post-admission hit | 21.79 /22.68 | 30 |
| Burn helper-cold /actually evicted hit | 21.62 /23.24 | 40 |
| Burn settled /cold miss added | 48.54 /41.28 | 65 |

Native timing varies; the small negative geometry difference is not a claimed
speedup. Complete current misses average 943.29/996.30 ms geometry and
79.80/66.72 ms burn (settled/cold). The readout includes actual provenance,
access checks, visible attempt status and publication. Six actual 512-entry
pressure preparations exercised bounded-cache eviction. Settled hit digest
payload reads are zero and all hits avoid native regeneration. Every miss
executes native generation once.

All 990 geometry features and their properties/bounds match the original after
removing only embedded private provenance. Aligned burn pixels and the complete
rasterio profile match. Actual embedded proofs are present; legacy admission
preserves output modes. These are warm-filesystem component means, not cold
storage, percentile or full HTTP/owner guarantees.

## Quality and test assessment

The shared helper keeps proof shape, input observation, retained attempts and
publication in one place; the services retain their existing native algorithms
and public envelopes. The same-call optimization avoids repeated native graph
acquisition while preserving fresh pre-observation, digest admission policy,
companion membership, resolved paths and complete-set physical/config guards.
No graph or descriptor is reused across requests. Candidate confinement and
canonical destination rechecks remain explicit. Status publication errors after
the replace commit are diagnostic rather than fictitious rejected publication.

Tests assert meaningful consumer outcomes: restored-time source/legend edits
change actual feature properties; native ABA preserves previous output; source
pixels and bound transforms change actual alignment; old auxiliary-bearing
outputs retain native compatibility; late destination/companion changes reject;
source-change/native-error boundaries stay visible. The actual canonical archive
regression retains failed and accepted producer records. Small native fixtures
make races deterministic rather than testing only signature helper equality.

Independent correctness revision 3 passes 15 probes, including joint mutation
while verifying the bound, disappearance between physical checks and hashing,
and unrelated EIO preservation. Security separately reviews target access,
confinement, post-commit status and same-call verification. The root's combined
Geneva/profile/archive gate passes 135 tests (36 warnings) in
`geneva_profile_archive_final_tests.log`; do not attribute that entire count to
Geneva alone.

Residual nonblocking debt: `_Inputs` and attempt helpers rely on the bounded
raster observation's tuple shape and private companion helper. Keep that coupling
inside this collaborator and cover shared-helper evolution with the existing
native tests. The diagnostic profiles show status/path work remains material;
retained observability is intentional, and no new descriptor cache or protocol
is justified. The representative 990-feature watershed is not a scalability
claim for fragmented or substantially larger HRU data. Preserve the explicit
uncached native branches for unsupported layouts.

## Original failures and remaining scope

`geneva_performance_initial_failure_review.md` retains the first failed gates
and its diagnosed admission-label harness error.
`geneva_performance_revision2_review.md` retains the corrected run's four failed
original gates and component diagnosis.
`geneva_performance_budget_amendment.md` records independent explicit ratification,
and the canonical specification/checkpoint was committed before this new run.
None of those records is overwritten or relabeled as an original-budget pass.

Archive directory-mode interoperability was independently found and corrected
outside this producer review; its dedicated security/restore evidence owns that
acceptance. Full service identities/groups, HTTP/kernel/browser workflows and
package-wide unresolved dependency boundaries still require their own final
runtime disposition.
