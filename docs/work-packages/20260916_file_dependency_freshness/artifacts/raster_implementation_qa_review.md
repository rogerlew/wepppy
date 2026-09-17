# C03/C04 corrected implementation QA and performance acceptance

**PASS for scoped implementation quality and the ratified representative
performance gates.** No unresolved maintainability/test-quality blocker was
identified in this bounded wave. This does not close the package, other raster
consumers, or production-equivalent runtime acceptance.

## Evidence and actual execution boundary

Final evidence is [the guarded benchmark](benchmark_raster_implementation_guarded.py),
[JSON](raster_implementation_performance_guarded.json),
[log](raster_implementation_performance_guarded.log) and
[machine acceptance](raster_implementation_budget_acceptance.json). The script
exited zero; **all 46 gates passed**. Module files and all seven selected copied
input files remained unchanged. The acceptance record binds the complete JSON
by SHA-256 and records exact helper/consumer source hashes.

Full source snapshots, the old Landuse source and manifest are retained at
`/wc1/batch/qa-raster-implementation-0648a5eb4663/`. Actual inputs/owners are the
unique disposable clones listed in the earlier raster baseline manifest. No
native operation or owner construction used a named project. The real NoDb
lock, persistence, management Parquet publication, catalog and completion hook
remain inside whole-operation timings. UID/GID are 1000/993; GDAL is 3.10.3.

The benchmark transparently measures the **actual
`observe_raster_dependencies` API** in both consumers, including eligibility,
sibling inventory, configuration and same-acquisition file/directory guards.
It adds no replacement observer or composed checks. C04 performs two actual
observations on hits and three on misses, because miss admission must validate
inside the eight-entry numerical cache. C03 performs two joint observations
plus its existing structure identity.

Paired C03 controls use exact original method definitions from `ceb715c08`
against the same hydrated owner, with each method version primed outside timed
hits. No duplicate NoDb class is imported. Three interleaved repeats cover each
phase. SBS settled-hit means use 30 repeats; miss/cold/pressure means use three.
These are filesystem-warm NFS measurements, not cold-storage/tail-latency
guarantees. Initial legacy admission is recorded separately from warmed controls.

## Final means and gates

All numbers below are milliseconds. C04's measured nonnative miss overhead
subtracts native time from the **same operation**; separate direct-native
controls are also retained so timing variability cannot manufacture a pass.

| C04 input | Settled hit | Cold / evicted hit | Settled / cold miss | Measured added miss work |
| --- | ---: | ---: | ---: | ---: |
| Original SBS, 599 KB | 9.83 | 10.80 / 12.25 | 58.63 / 58.57 | 10.39 / 15.92 |
| Large-pixel cropped SBS, 425 KB | 9.96 | 9.44 / 10.34 | 483.96 / 488.08 | 10.25 / 14.34 |

Both satisfy the **25-ms complete settled hit** and **50-ms added native-miss**
limits. Native summaries exactly match direct native results. Initial admission
is 58.05/478.78 ms and calls native once. Cold/evicted hits do not call native;
settled hits perform neither native work nor full payload hashing.

| C03 actual input / phase | Whole operation | Complete validation | Actual lock occupancy | Added whole / lock vs paired original |
| --- | ---: | ---: | ---: | ---: |
| WBT settled hit | 103.94 | 13.94 | 78.32 | 11.56 / 13.19 |
| WBT settled miss | 145.91 | 13.69 | 118.04 | 14.58 / 13.23 |
| WBT cold hit | 112.90 | 18.28 | 85.26 | 19.98 / 18.97 |
| WBT cold miss | 155.75 | 18.25 | 129.02 | 2.90 / 4.26 |
| WBT evicted hit | 115.70 | 19.32 | 87.89 | 20.73 / 21.03 |
| TOPAZ settled hit | 1,010.79 | 45.86 | 801.42 | 29.04 / 19.66 |
| TOPAZ settled miss | 1,748.97 | 47.91 | 1,535.03 | 43.56 / 30.78 |
| TOPAZ cold hit | 1,310.52 | 343.26 | 1,109.41 | 325.76 / 324.33 |
| TOPAZ cold miss | 2,020.21 | 331.33 | 1,818.01 | 296.31 / 296.70 |
| TOPAZ evicted hit | 1,321.90 | 331.38 | 1,117.12 | 358.60 / 350.35 |

C03 satisfies **75/400 ms complete validation** and **100/450 ms added whole
operation and lock occupancy**, settled versus cold/evicted respectively.
Validation and total deltas differ because native/persistence time varies;
neither is excluded from its applicable gate. The 41.43-MB TOPAZ/AAIGrid pair
retains actual numerical reuse. Legacy signatures invoke native once and
establish the new representation; their measured complete validation is
17.85 ms WBT and 324.67 ms TOPAZ.

Twelve actual eviction exercises fill **both** bounded ordinary-digest LRUs
with 512 distinct admitted pressure files. The numerical caches remain intact.
Each evicted target rehashes its bytes while preserving zero native calls on
hits. Complete C03 cold/evicted accesses hash twice the input set: 814,096 bytes
for WBT and 82,859,480 bytes for TOPAZ. C04 cold misses hash three times because
of the internal admission check. All settled representative hit and miss paths
perform zero full digest payload reads; this counter excludes native GDAL pixel
and metadata reads. Cache capacity was not increased.

Actual management values and Parquet row types/values equal the original
controls. Both disposable owners' `landuse.nodb` and Parquet modes remain 0644.
The existing actual `.man` synthesis/preparation compatibility probe is retained
by the correctness reviewer; this performance run does not repeat or claim a
full WEPP/RQ/browser workflow.

## Quality, tests and retained failures

The separation of `RasterDependencyObservation.signature` from `read_guard`
addresses two distinct requirements: completed same-byte metadata operations
may reuse numerical data, while observed changes during materialization reject
admission. Dataclass equality/hash explicitly exclude the guard; consumers
compare the two **current acquisition** guards around native work. C04 checks
inside the cached function before admission and outside it for cache hits.
C03 stages its count/signature update and deep-copies reused runtime-generated
management summaries, preserving prior values on rejection. These changes are
cohesive and avoid a second native decoder or persistent cache.

Tests exercise actual GTiff/AAIGrid reads and native results, restored-mtime
rewrites, same-byte operations, source aliases, native-used world names,
auxiliary changes, unverified native compatibility, and deterministic changes
during observations/native calls. The corrected A→B→A regressions expose changed
bytes to native work and restore them before post-observation; the result must
raise ESTALE and preserve prior cache state. Directory guards also distinguish
temporary companion membership without putting timestamps into cache identity.
The focused affected run retains **163 passed, 1 skipped, 4 warnings**;
stubtest passes. This review inspected that evidence rather than adding test
load during the isolated timing window.

Original intermediate evidence remains visible:

- `raster_implementation_performance.json/.log` is the superseded partial run
  before cross-operation guards. Its pause and termination records prove no
  further timing samples after the safe pause; `acceptance_passed` is false.
  The final run uses separate `_guarded` files.
- `raster_implementation_correctness_guard_final.log` retains a fixture-only
  detached-owner logger failure; the corrected fixture's
  `raster_implementation_correctness_roundtrip_after.log` passes. Production
  code did not change for that fixture correction.
- `raster_read_guard_security_after.log` retains an incorrect probe assumption
  that temporary PAM metadata changes native SBS class counts. The actual
  negative control keeps those counts unchanged while rejecting directory
  drift; `raster_read_guard_security_probe_revision2.log` passes all three
  corrected probes. Actual changed-byte A→B→A native output is separately shown.

Residual debt is bounded: verified driver/companion/configuration coverage is
explicit and must be reevaluated when that coverage or native versions change.
Unverified native formats retain their uncached performance cost; these local
fixtures do not justify a general recursive framework. Most regression fixtures
are small, so full runtime and broader workload evidence remains a separate
gate. No speculative refactor or additional cache architecture is recommended.
