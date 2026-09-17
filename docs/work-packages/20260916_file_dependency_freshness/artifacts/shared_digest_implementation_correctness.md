# Shared ordinary-file digest implementation correctness review

Independent reviewer: `freshness_correctness`, 2026-09-17 UTC. Reviewed new
`all_your_base/file_digest.py/.pyi`, both consumer diffs after checkpoint
`dd5d09ca7`, regression tests, retained actual-caller probes, focused/stub logs
and benchmark source/results. No production code or tests edited by reviewer.

**Verdict: PASS for scoped code correctness; all three validation gaps resolved.**
No major implementation defect identified. Broader runtime/package acceptance
and remaining inventory findings are not covered by this pass.

## Findings and follow-up evidence

| ID | Severity | Finding and smallest follow-up |
| --- | --- | --- |
| SHARED-C01 | Low, resolved | Added `test_interleaved_paths_keep_both_caches_bounded` uses 600 real paths, admits their digests, verifies both caches remain at 512 and revisits old/new entries. The separately reviewed security probe fills 512 observation slots while retaining the target's admitted digest, then directly verifies reobservation and fresh mature admission read bytes before settled reuse. |
| SHARED-C02 | Low, resolved | Actual `_build_features_export_artifact` now has a helper-failure case proving omission. The executable wrapper failure test asserts RegistryError and preservation of the original PermissionError as its cause. Real file admission remains active; narrow hooks schedule the hash failure. |
| SHARED-C03 | Low, resolved | Added read-only timing for an actual 164,591-byte features-export ZIP on `/wc1/runs`: 4.43 ms cold, 0.291 ms settled mean and zero settled misses. This closes the representative export-helper timing gap; restarted endpoint acceptance remains separate. |

## Cache and coherent-read assessment

The helper keys by absolute path and full device/inode/size/mtime/ctime version.
Both observation and digest LRUs have capacity 512. New observations use a
monotonic clock and hash without cache admission for one second; the mature
lookup hashes freshly through `_digest` before reuse. Observation generation
participates in its key, so a surviving older digest cannot be resurrected after
observation eviction. `use_cache=False` bypasses observation and reusable-digest
lookup and reads bytes. No new filesystem resolution or time heuristic appears.

Every call opens the path, verifies regular-file status and descriptor/path
agreement, and repeats generation checks before returning, even on warm hits.
Cold reads use a second verified descriptor with captured-size-plus-one bounds
and exact final byte count. Growth, truncation and replacement fail explicitly;
exceptions do not return an empty digest or get admitted by the LRU. The tests
verify settled reuse opens once without content reads, uncached mode reads,
and prior success cannot bypass a later open error.

Directory-backed rasters and virtual members are outside these two callers'
accepted ordinary-file domain. No directory compatibility fallback or traversal
is introduced. Permitted ordinary symlinks remain followed. This helper is not
an authorization or no-follow primitive, and the post-fire helper is untouched.
The existing coherent metadata-on-open, timestamp-quantum and point-in-time
limitations remain; this is not arbitrary-writer snapshot isolation.

## Caller assessment

The export wrapper checks supplied size/mtime before and after hashing, also
requiring unchanged device/inode/ctime across that interval. It therefore rejects
observable changes between the wrapper precheck and helper read. Its test hook
changes the real file before invoking the real helper and verifies rejection.
The caller's reported size cannot silently come from the old observation while
the digest comes from a visibly newer file. Existing provenance, containment,
authorization and best-effort omission handling remain unchanged.

The executable wrapper retains `is_file`, read/execute checks and original
RegistryError translation. The unbounded private dictionary is removed; provider
selection, role ordering and identity formatting are unchanged. The new registry
regression verifies that real restored-time byte changes propagate into both
component identity and overall registry revision. Execute-bit loss continues
to fail before hashing.

## Retained evidence

`shared_digest_focused.log`: **151 passed**. The initial stubtest found missing
`__all__` declaration in the stub; that original failure is retained, and
`shared_digest_stubtest_revision2.log` reports success after the declaration was
aligned. These are reviewed retained runs, not additional reviewer reruns.
Follow-up `shared_digest_review_tests.log` records **76 passed**, covering the
600-path eviction and actual caller-error cases. The permitted-symlink addition
checks both original and changed bytes through a real symlink;
`shared_digest_symlink_tests.log` records **7 passed**.
`shared_digest_security_probe.py/.log` additionally records actual observation
LRU eviction with a surviving digest, zero settled content bytes, allowed
symlink reads and actual read/execute access loss under UID 1000/GID 993. This
reviewer checked its real-file scheduling and read-count assertions.

`schema_digest_after.json` returns the correct new digest after equal-size and
restored-mtime mutation. `registry_digest_after.json` records **1,000 real rapid
rewrites, 671 identical metadata versions and zero stale digests**, compared with
452 stale results in the retained baseline. The collision probe does not sleep
or fabricate filesystem versions.

`shared_digest_benchmark.json` records 2.64 MB executable cold hashing at
**9.37 ms**, settled mean **61.78 microseconds**, and 26.4 MB DEM cold hashing at
**92.87 ms**, settled mean **95.66 microseconds**. Both have zero settled cache
misses over 100 lookups. Its explicit sleep is only to measure the settled
admission branch, separate from the unslept failure probe. The benchmark takes no
production mutation and makes no native raster-semantic claim.

The expanded `shared_digest_benchmark_with_export.json` retains the actual export
timing above. Executable and DEM settled means in that run are 65.66 and 94.08
microseconds, each with zero misses, so all three remain below the 1 ms budget.
These measurements time the shared helper; whole endpoint and provider-loader
latency are covered by later runtime acceptance rather than inferred here.

The reviewer also resolved the README contract link against its actual parent
directory: `../../docs/schemas/file-dependency-freshness-contract.md` correctly
reaches the existing repository contract. An earlier informal suggestion to add
another parent segment was mistaken; no link change is needed.

No scoped correctness finding remains open. Finish final applicable sanity and
restarted endpoint/binary-identity acceptance before delivery. The shared helper does not
close feature-export dependency fingerprints, indirect raster dependencies,
report caches or other unresolved package consumers.
