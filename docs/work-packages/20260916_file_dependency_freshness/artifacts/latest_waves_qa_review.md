# Derived main-file and shared digest implementation QA

Reviewer: independent `freshness_qa`, 2026-09-17 UTC. Reviewed current changes
after derived-input checkpoints `b8c63ab1e` / `dbec83d30` and shared-digest
checkpoint `dd5d09ca7`. No production code or tests were edited or rerun by this
reviewer; validation counts below are inspected retained evidence.

## Disposition

**PASS for both bounded implementations' maintainability and test quality.
LQA-01 and LQA-02 are resolved by follow-up evidence.** No medium/high QA finding or additional
production defect was identified. Derived-mainfile correctness/security reviews
have passed after their recorded corrections. Shared-digest implementation
correctness also passes after its validation follow-ups; its final security
disposition remains a separate gate from this QA assessment.

This does not close C01 raster dependencies, any remaining inventory consumer,
complete-input lock/performance budgets, or final runtime/archive acceptance.

## Actionable follow-ups

| ID | Severity | Evidence and smallest follow-up | Disposition |
| --- | --- | --- | --- |
| LQA-01 | Low, consumer error coverage; resolved | Initial tests asserted helper errors without exercising final discovery omission or registry error translation. | Verified actual `_build_features_export_artifact` omits an artifact after the injected helper failure; `test_executable_hash_failure_keeps_registry_error_translation` verifies `RegistryError` and the exact original error cause. Covered by `shared_digest_review_tests.log`, 76 passed. |
| LQA-02 | Low, allowed-path coverage; resolved | Initial direct-helper coverage did not exercise its intentionally permitted ordinary symlinks. | Verified a real symlink returns the empty target digest and then the changed target bytes' digest. Covered by `shared_digest_symlink_tests.log`, 7 passed. This establishes allowed-path compatibility without changing post-fire's separate no-follow policy. |

## Derived main-file wave

`wepppy/nodb/_derived_build.py:file_signature` appends an uncached byte digest
to the existing transaction identity. The existing mtime conflict rule remains;
inode/ctime checks guard each read without becoming new between-observation
equality fields. Both callers keep their existing snapshot comparisons and
publication ordering. The changes stay localized and do not alter numerical
readers, lock ownership, rollback identity, or recovery behavior.

The explicit directory branch preserves the earlier root metadata identity and
returns `None` for the digest. It is selected by file type, never by catching a
failed regular-file read. Its comment and optional return annotation make the
unverified directory-member state visible. It must remain explicit while the
recursive raster closure work is unfinished.

`tests/nodb/test_derived_file_signature.py` uses real hard links, chmod, empty
files, replacement, restored-time byte changes, growth, truncation and FIFO
rejection. Narrow reader wrappers schedule the concurrent operations while real
descriptor checks and bytes remain in use. The error test verifies the exact
`PermissionError` object. The native compatibility case creates a Zarr dataset
with GDAL and reads it through `identify_median_single_raster_key`, asserting
actual numerical output instead of merely claiming the path was accepted.

Both restored-time finalizer regressions now preserve exact previous output
and NoDb bytes. The RAP fixture generates a valid prior parquet via `analyze`,
so normal fresh hydration participates in the failure test. Numerical work is
injected in these finalizer tests; they prove the publication comparison and
preservation boundary, not end-to-end native processing.

`derived_main_review_tests_revision2.log` records **46 passed**. The earlier
44-pass/1-failure fixture run and original directory rejection remain retained,
with explicit correction in the independent correctness/security reviews.

## Shared ordinary-file digest wave

`wepppy/all_your_base/file_digest.py` is a small, focused owned utility. Two
confirmed byte-digest consumers share it without importing run authority or
raster traversal into the helper. Its module/API documentation distinguishes
permitted ordinary symlinks from the separate no-follow domain opener. Both
existing caller error boundaries and executable read/execute checks remain
visible at their original call sites.

The two bounded LRUs have distinct roles. The observation value is part of the
digest cache key, with a comment explaining why eviction must start a fresh
admission generation. `use_cache=False` reaches the same verified read body
without querying either cache. Warm calls still open/check the path; cold reads
bound growth and compare final byte count, descriptor version and pathname.
There is no generic retry, fallback digest, persistent cache or new dependency.

The autouse cache-clearing fixture isolates global cache state between tests.
The deterministic clock test checks young non-admission, settled no-byte-read
reuse, access reopening, observation removal with a surviving old digest, fresh
admission and explicit uncached reading. Separate real-clock repeated rewrites
exercise filesystem collisions without sleeps or mocked stat values. Drift
tests verify both rejection and absence of a cached result.

Caller tests exercise actual restored-time output hashes and actual executable
identity. The registry integration assertion verifies propagation into both
component `source_revision` and complete registry `revision`. The output wrapper
test schedules a change after its first observation and confirms the supplied
metadata expectation cannot be paired with a later incompatible digest. The
downstream failure cases in LQA-01 now explicitly confirm omission and translated
error cause. The follow-up 600-path test also fills both LRUs, verifies each
remains at 512 entries, and revisits both early and recent files.

Residual non-blocking maintenance debt: the hash loops in this helper, the
derived transaction helper and post-fire are similar. Their openers, returned
identity, directory support, error contracts and cache rules differ. Consolidate
only after those differences have explicit shared requirements; duplication
alone does not justify widening this bounded wave. Cache tests reference private
LRUs intentionally to verify admission, rather than adding a production cache
management API solely for tests.

## Retained evidence and remaining gates

- `shared_digest_focused.log`: **151 passed** across the new helper, output
  discovery/schema routes, and registry serializer suites.
- `shared_digest_review_tests.log`: **76 passed** with actual cache-capacity
  eviction and both consumer error-boundary follow-ups.
- `shared_digest_symlink_tests.log`: **7 passed** after adding allowed-symlink
  and current-target-byte coverage to the helper suite.
- `registry_digest_baseline_probe.json`: 452 stale digests in 1,000 actual
  registry-helper rewrite pairs. `registry_digest_after.json`: **zero stale
  digests**, including 671 identical-version rewrites. The different collision
  counts reflect separate real filesystem runs, not a controlled timestamp set.
- `schema_digest_after.json`: restored-size/mtime output SHA matches the new
  bytes and differs from the previous SHA.
- `shared_digest_stubtest_revision2.log`: **success for the public helper**.
- `shared_digest_benchmark.json`: the 2.64 MB executable hashes in 9.37 ms and
  settles at 61.78 microseconds/lookup; the 26.41 MB reference DEM hashes in
  92.87 ms and settles at 95.66 microseconds/lookup. Both have zero settled
  misses across 100 calls and meet the retained sub-millisecond warm budget.
- `shared_digest_benchmark_with_export.json`: the actual 164,591-byte export ZIP
  on `/wc1/runs` hashes in 4.43 ms, settles at **0.291 ms/lookup**, and has zero
  settled misses. Executable and reference-raster measurements also remain
  within budget in that run.
- `derived_inputs_benchmark.json`: 39 small RAP rasters, 564,058 total bytes,
  require 0.536 seconds first pass and 0.035 seconds second pass. No lock was
  acquired; this is not a complete watershed/MOFE input-set or lock-occupancy
  benchmark.

The shared benchmarks now cover helper calls on an actual export, executable,
and large reference raster. Full endpoint overhead, interleaved caller workloads
and other deployment mounts remain runtime acceptance concerns. The benchmark's wait to
enter settled admission is appropriate and separate from the no-sleep rapid
rewrite regression.

Complete recursive VRT/auxiliary/VSI/directory-member freshness remains OPEN.
Main-file hashing cannot establish that native raster inputs are unchanged.
Final full sanity after the last edits, remaining consumer dispositions,
restarted endpoint/binary/native workflow acceptance under actual identities
and mounts, and archive/restore evidence remain required. These scoped QA
passes do not authorize a claim that the repository freshness package is done.
