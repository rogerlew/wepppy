# C03/C04 consumer baseline and checkpoint QA

**Disposition: PASS for the bounded GTiff/AAIGrid design and the measured
performance targets below; implementation acceptance remains pending.** Reject
the earlier blanket 100-ms cold-miss overhead proposal. No production or test
files were edited, and no new numerical formula or native reader was introduced.

Reviewed the canonical [raster contract](../../../schemas/raster-dependency-freshness-contract.md),
[checkpoint decision](raster_cache_contract_decision.md), actual
`Landuse.build_managements`/NoDb locking/publication, SBS summary calls, and the
retained correctness/security findings. The narrower verified subset, explicit
uncached native compatibility, joint two-raster coherence and post-check-before-
admission requirements are appropriate. AAIGrid coverage is justified by the
actual maintained TOPAZ consumer, not speculative driver support.

## Retained measurements

[Native and composed baseline script](benchmark_raster_consumers.py),
[JSON](raster_consumer_performance_baseline.json) and
[log](raster_consumer_performance_baseline.log) retain source sizes, identities,
actual native calls, content-hash read bytes and complete management/lock timings.
[Warm-owner controls](benchmark_raster_management_warm.py),
[JSON](raster_management_warm_baseline.json) and
[log](raster_management_warm_baseline.log) exclude first-use initialization.
[Interleaved controls](benchmark_raster_management_interleaved.py),
[JSON](raster_management_interleaved_baseline.json) and
[log](raster_management_interleaved_baseline.log) alternate original/composed
operations three times per phase on the same hydrated owner.

Large outputs remain browsable at
`/wc1/batch/qa-raster-consumers-0fa74f3f2f95/benchmark-manifest.json` and the unique
clone directories recorded there. Named run inputs were copied read-only, with
content hashes and device/inode/size/mtime/ctime checked before and after. Native
and owner operations used the disposable copies. Unique clone basenames avoid
sharing named-run notification identities. The installed GDAL is 3.10.3; the
container identity is UID 1000/GID 993.

All times below are local means in milliseconds on filesystem-warm copied NFS
inputs. No OS-cache eviction or cold-storage claim is made. The probe observer
opens the real local datasets, inventories them again after hashing, checks
member versions, and includes selected/resolved identity and MOFE structure.
It deliberately covers only these simple fixtures. It does **not** implement
the final companion/configuration/pre-open security policy; composed timings
are cost evidence, never proof of implemented conformance.

| Consumer/input | Size and native shape | Actual uncached native mean | Existing settled hit | Composed settled hit |
| --- | --- | ---: | ---: | ---: |
| C04 original Grizzly Creek SBS | 599,196 bytes; 714 × 836 GTiff | 42.37 | 0.009 | 9.98 |
| C04 cropped SBS | 424,964 bytes; 2,630 × 2,509 GTiff | 476.18 | 0.015 | 9.19 |
| C03 curable-program | 407,048 bytes; 306 × 263 GTiff pair; 115 hillslopes | 40.59 | 109.05 | 109.61 |
| C03 beneficiary-forfeit | 41,429,740 bytes; 2,413 × 2,452 AAIGrid + PRJ and GTiff; 4,903 hillslopes | 762.08 | 1,000.91 | 1,043.12 |

C03 hit figures include actual management rebuilding, the real NoDb lock,
persistence, `landuse.parquet`, catalog publication and the ordinary completion
hook. They are not count-dictionary lookup timings. The first small-owner miss
took 3.90 seconds because of initialization; it is retained but excluded from
steady-state overhead comparisons. Warm-owner control misses were 134.45 ms
for WBT and 1,675.32 ms for TOPAZ. Variability between runs is why the additional
interleaved controls are retained.

| Interleaved C03 phase | Existing whole operation | Composed whole operation | Complete validation | Added lock occupancy |
| --- | ---: | ---: | ---: | ---: |
| WBT settled hit | 154.33 | 106.22 | 19.39 | 11.52 |
| WBT settled miss | 121.24 | 148.21 | 17.98 | 25.90 |
| WBT helper-cold miss | 120.30 | 145.85 | 21.23 | 23.25 |
| TOPAZ settled hit | 893.77 | 945.11 | 50.67 | 54.29 |
| TOPAZ settled miss | 1,603.84 | 1,661.49 | 47.07 | 58.06 |
| TOPAZ helper-cold miss | 1,580.49 | 1,916.06 | 328.31 | 334.11 |

The small hit's negative whole-operation delta reflects publication variability,
not a speedup from validation; its measured validation and added lock are both
positive. The real warm TOPAZ lock already occupies about 752 ms on hits and
1,525 ms on misses. Avoid interpreting the validation budget as a budget for
the entire existing management computation.

Settled digest payload reads were zero in the main probe; native GDAL metadata
reads are not counted as digest payload reads. The cold paired operation read
82,859,480 hash bytes, twice the 41.43-MB source set. A single cold paired
observation took 161.64 ms, and the interleaved complete cold validation took
328.31 ms. The 100-ms blanket cold overhead is therefore disproved, rather than
silently relaxed after implementation. Actual shared-cache pressure eviction
is still an implementation acceptance gate; clearing the helper cache here is
not labeled a 512-entry eviction measurement.

## Ratified checkpoint targets

Ratify these **provisional implementation targets** for the retained
representative local inputs, measured as means in an isolated timing window:

| Boundary | Target | Evidence and headroom |
| --- | --- | --- |
| Complete C04 settled cache hit | ≤25 ms | Composed 9.2–10.0 ms; include both observations and all final guards. |
| C04 native miss, added cost | ≤50 ms over actual native baseline | Composed overhead about 9–13 ms, including helper-cold hashing on these SBS files. |
| Complete C03 paired validation, settled | ≤75 ms | Actual composition 18–51 ms; allows the required final eligibility/coherence guards. |
| Complete C03 paired validation, helper-cold/admission/evicted | ≤400 ms | Large paired composition 328 ms; retaining both byte observations is required. |
| C03 whole operation **and** lock occupancy, added settled cost | ≤100 ms each over paired same-owner controls | Large hit/miss added lock 54–58 ms and whole operation 51–58 ms. |
| C03 whole operation **and** lock occupancy, added cold/evicted cost | ≤450 ms each over paired same-owner controls | Large cold added whole/lock 336/334 ms. |

The 75-ms bound replaces the candidate 50-ms complete validation target before
implementation: the realistic large input already takes 50.67 ms before the
final guards. The 400/450-ms cold targets are size-specific evidence for the
41.43-MB representative set, not universal latency guarantees. The earlier
single-graph discovery target cannot substitute for any whole-consumer gate.
All required path/access/configuration/companion/coherence work must remain in
the actual timing. If the implementation misses these targets, retain the miss
and profile it; this review does not authorize changing capacity, weakening
authority checks, adding persistent caches or silently revising the budget.

## Quality and valid-state acceptance

The final observer should keep eligibility/discovery, byte observation and
consumer admission distinguishable. Return or log a concrete unverified reason
so native compatibility paths remain diagnosable. Avoid a broad catch that
turns missing/denied/malformed dependencies into reusable sentinel identities.
No VRT/XML framework is warranted by this bounded consumer requirement.

The native baseline confirms that AAIGrid bypass would add about 762 ms of
counting on every large TOPAZ cache hit and hold the existing management lock
for that extra work. The revised AAIGrid subset addresses this measured valid
state. Conservative PAM/unproven-layout bypass remains acceptable; its actual
native success/error and any representative performance impact must be explicit.

Implementation tests and acceptance must demonstrate:

- Actual SBS class counts and MOFE management areas change after equal-size,
  restored-mtime source rewrites; same-byte touches/replacements reuse the
  numerical result after validation. Assert native-call counts as well as values.
- Both rasters and current MOFE key structure form one coherent set on hits and
  misses. Labels-only changes preserve count reuse while updating management
  metadata. Legacy private signatures miss once without a migration.
- A change during native work or between observations never admits an old-key
  result. Preserve previous counts/signature, management objects (including
  runtime-generated summaries), files and Parquet after rejection.
- Pre-open companion/configuration eligibility prevents the retained eager
  remote-read cases. Unsupported VRT/Zarr/VSI/PAM cases reach the same native
  operation and preserve its existing success/error boundary; source symlinks
  and native-readable but directory-unlistable inputs remain compatible.
- Absent, empty, malformed and denied files cannot hit old cache entries.
  Auxiliary addition/removal and link/configuration changes are observed on
  reuse. The SBS numerical cache remains bounded at eight entries.
- Actual guarded settled hits perform zero full payload hashes, and real
  512-entry digest pressure produces correct cold admission without rebuilding
  unchanged numerical results. Rerun complete hit/miss/lock measurements using
  the final implementation, including required pre-open policy work.

The probes preserved actual management dictionaries and Parquet row types/values
and invoked ordinary NoDb persistence. They did not generate and compare final
`wepp/runs/*.man` files; downstream WEPP propagation remains required. Full
inventory, C01/C02/C05/C06 closure, production-equivalent browser/runtime workflow
and package-wide acceptance remain open outside this checkpoint. There is no
additional speculative redesign recommendation.
