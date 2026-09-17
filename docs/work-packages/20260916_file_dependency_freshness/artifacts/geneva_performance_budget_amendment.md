# Geneva performance budget amendment: independent QA decision

**Ratify the explicit amendment below for fresh implementation acceptance.**
The original budgets failed and remain failed in the retained evidence. This
review does not convert those runs to passes. The amendment requires canonical
specification/checkpoint adoption and a new complete actual-service measurement.
No runtime code, guard, scientific calculation or output behavior changes here.

## Amended representative mean budgets

| Complete service boundary | Original | Amended | Retained measured basis |
| --- | ---: | ---: | --- |
| C05 geometry hit, settled | 40 ms | 40 ms | Current 28.29 ms; unchanged. |
| C05 geometry hit, cold/evicted | 75 ms | 75 ms | Current 29.51/29.99 ms; unchanged. |
| C05 native miss, added to paired ancestor | 100 ms | 125 ms | Current cold added 106.47 ms, including actual proof/attempt/publication. |
| C06 burn hit, settled | 25 ms | 30 ms | Current 21.99 ms; secondary settled mean 25.07 ms; isolated current mean 21.31 ms. |
| C06 burn hit, cold/evicted | 40 ms | 40 ms | Current 26.71/22.52 ms; unchanged. |
| C06 native miss, added to paired ancestor | 35 ms | 65 ms | Current paired added 51.73 ms settled /37.10 ms cold; isolated same-call nonnative work 38.42 ms. |

Both miss limits apply to complete settled and helper-cold operations. Settled
hits still require zero digest payload reads and zero native generation.
Admission/eviction must use the actual bounded 512-entry digest caches. Keep
whole operation timing, existing native work and every required proof, access,
coherence, status and publication operation inside the measured boundary.

These are local means for the already reviewed copied 990-feature Geneva
workload. They are not storage latency guarantees, percentile service objectives,
universal raster-size budgets or end-to-end HTTP/RQ limits. The original scope,
representative data, ancestor `31f77bef1` and native parity requirements stay the
same. Larger/fragmented HRU workloads need separate evidence.

## Why this is a justified correction

The preliminary composition measured native consumers plus input observations.
It did not implement the subsequently required retained attempt/status lifecycle,
complete target-proof/permission checks and atomic publication. Its alignment
miss estimate was 34.19 ms total against 29.35 ms native, only 4.84 ms added.
The final code must do substantially more than that prototype. Treating the
prototype as a complete publication-cost estimate was the checkpoint mistake.

A measured implementation optimization has already removed duplicate native
source/bound acquisition. Current burn hits use three raster observations rather
than five, and misses use two rather than four; the final same-call validation
retains digest admission policy, companion membership and joint physical/config
checks. Independent correctness covers those preserved boundaries. The isolated
current miss spends 24.40 ms in native stacking and 38.42 ms outside it. Its
remaining inclusive costs include 9.62 ms input acquisition, 2.26 ms final
validation and 11.44 ms in two status publications, with confined path resolution
also visible. These inclusive costs overlap and are not summed to manufacture
a threshold. Duplicate native acquisition is no longer the remaining cause.

The proposed 65-ms added-miss limit gives about 26% headroom over the measured
51.73-ms paired mean; the 125-ms geometry addition gives about 17% over 106.47 ms.
The 30-ms settled burn limit gives about 20% over the valid 25.07-ms secondary
mean. This is a bounded allowance for measured complete operations and local
variation. It is not the mathematically smallest number above a favorable run;
such a cutoff would be brittle on the observed filesystem/native workload.
Unchanged hit and cold budgets continue to constrain routine reuse.

The absolute impact is explicit: measured burn misses are 88.78 ms versus
37.04 ms in the paired settled ancestor and 59.52 ms versus 22.42 ms helper-cold;
geometry's cold miss is 1006.37 ms versus 899.90 ms. Accepted repeated reuse is
about 22–28 ms and performs no native regeneration. The amendment does not claim
a miss speedup or erase this additional cost.

Further speculative state, cross-request descriptor retention or a new native
protocol is not justified by this bounded local cost. Dropping status evidence,
path authority, content checks or publication validation is also unacceptable.
Keep the implemented optimizations and explicit evidence boundaries; evaluate
another implementation change only against a concrete new bottleneck or failed
amended acceptance condition.

## Evidence preservation and final gate

Retain all original scripts, JSON, logs and output generations:

- `geneva_consumer_performance_baseline.json/.log` and
  `geneva_consumer_performance_qa.md`: incomplete preliminary cost composition.
- `geneva_implementation_performance.json/.log` and
  `geneva_performance_initial_failure_review.md`: original failures and the
  explicitly diagnosed first burn admission-label error.
- `geneva_implementation_performance_revision2.json/.log` and
  `geneva_performance_revision2_review.md`: corrected preparation, optimized
  actual code, four failed original gates and zero settled payload reads.
- `geneva_alignment_component_profile_revision2.json/.log` and corresponding
  hit/miss profiles: isolated required-work diagnosis, not replacement acceptance.

Do not rewrite the original `acceptance_passed: false` records or their limits.
The next run must have new filenames and explicitly identify this amendment,
record source-module hashes, prepare observation before admission waits, use
actual target-proof/publication code, and retain all samples. Remeasure paired
native misses, complete hits, actual eviction, no-read/no-native reuse, generated
features/pixels/profile, permissions and input/module immutability. If a revised
gate fails, retain that failure and investigate; this decision is not permission
to keep increasing a limit.

Fresh performance acceptance is still pending. Full owner/HTTP/RQ/browser
acceptance and the separately confirmed archive directory-mode issue remain
open; this cost decision closes none of those boundaries.
