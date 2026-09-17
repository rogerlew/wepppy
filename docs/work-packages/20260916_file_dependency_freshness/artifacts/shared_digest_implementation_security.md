# Shared ordinary-file digest implementation security review

## Findings and disposition

**PASS for this scoped implementation; no open scoped findings.** Reviewed
2026-09-17 UTC against checkpoint ancestor
`dd5d09ca7c22cb66fa07ea4ea220fc2fb33e49c9`. This pass does not close the package
or replace outstanding full runtime acceptance. No production/test files were
edited by this reviewer.

Reviewed source SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `wepppy/all_your_base/file_digest.py` | `d090094983c4f7575801969a1339ae3306745f6ff93aa100c037d83dd7fb9ee7` |
| `wepppy/all_your_base/file_digest.pyi` | `4a9fa1f5e3296baeb5e986b6f5e4ed83f07daa38aa4d2b499b4b16c84ff91ae5` |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | `9f3369d3a35bae6f67c2e489dcc38f0145710c3fe47847a969bd53c59f1f7dc5` |
| `wepppy/nodb/config_builder/registry.py` | `47a4ca7f1ef78058533748fa97ffb463df3cb35b18a9785094eeb3ea5020e86c` |

## Integrity, access and noninterference

`sha256_file` opens the original absolute path on every call, including a cache
hit. It verifies a regular descriptor and current path association using device,
inode, size, nanosecond mtime and ctime. Cold hashing verifies the reopened
descriptor against that same version, bounds logical reads by captured size
plus one byte, checks exact final byte count and descriptor/path agreement, and
never hashes beyond the captured size. The outer descriptor/path checks also
run after cached or uncached computation. Observable drift fails explicitly;
filesystem errors propagate rather than yield empty or old content.

The two 512-entry LRUs implement the accepted admission interval. Reads during
the first monotonic second bypass the digest cache, maturity computes a fresh
digest, and the observation-generation value participates in its cache key.
An evicted observation therefore cannot revive a surviving earlier digest.
`use_cache=False` bypasses both reuse and observation insertion. Failed digest
computations do not populate the reusable cache.

The output wrapper checks caller size/mtime before and after hashing and also
checks device/inode/ctime across the call. It cannot silently pair old advertised
size with a new-generation digest after a wrapper-only precheck. Existing
artifact resolution, regular-file admission, run containment, finished-job/run
checks and omission/error boundaries are unchanged. No authorization, response
schema, endpoint or download behavior is modified by these diffs.

Registry `is_file` and `R_OK | X_OK` checks still precede every digest call.
Filesystem errors retain the existing `RegistryError` message and original
exception cause. Binary role selection and revision formatting are unchanged;
changed executable bytes now change the actual registry/component revisions.
No binary execution or permission mutation was introduced. The helper follows
allowed symlinks; post-fire's specialized no-follow code remains untouched.

## Retained test and probe evidence

Author logs inspected:

- `shared_digest_focused.log`: **151 passed**, 6 warnings, 14.64 seconds across
  helper, output discovery/schema and registry suites.
- `shared_digest_review_tests.log`: **76 passed**, 6 warnings, 11.32 seconds.
  Adds 600 interleaved paths that actually mature digest entries and verify both
  LRUs remain at 512; preserves artifact omission and RegistryError causes.
- `shared_digest_symlink_tests.log`: helper rerun after allowed-symlink coverage.
  The test checks both initial identity and subsequent changed target bytes.
- `shared_digest_stubtest.log`: retained initial failure because stub `__all__`
  did not export the runtime name. `shared_digest_stubtest_revision2.log`
  confirms the corrected stub passes. The first failure is not erased or counted
  as a successful gate.

The production tests use real same-size/restored-mtime writes, real grow/truncate/
replace hooks, empty/missing files, metadata-only operations, uncached access,
zero-read settled cache hits and fresh admission after observation reset. Output
tests cover caller expectations and drift before the helper opens. Registry
tests preserve execution-access rejection and prove full registry revision
propagation from real executable-fixture changes.

The actual registry probe in `registry_digest_after.json` observes **671 equal
metadata versions in 1,000 iterations, zero stale digests**. The original
452-stale result remains in `registry_digest_baseline_probe.json`. Both use the
real clock and actual helper with disposable files; no binary is executed.
Different collision counts reflect timing, not an asserted universal guarantee.

Independent reviewer command:

```text
wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/shared_digest_security_probe.py
```

`shared_digest_security_probe.log` exits 0 under UID 1000/GID 993. It forces
actual observation-LRU eviction with 512 other real paths while the original
digest survives, then verifies that both the new observation read and the
subsequent admission read consume fresh bytes. The settled call reads zero
content bytes. Allowed symlinks work; real chmod-based loss of read permission
fails, and removal of execute permission still raises RegistryError. Clock
injection schedules admission branches only, not metadata or rewrite evidence.

## Performance and remaining scope

`shared_digest_benchmark_with_export.json` uses the real WEPP executable, the
26.4 MB run raster and an actual features-export ZIP. Cold times are 10.49 ms,
96.09 ms and 4.43 ms respectively. Settled means are 0.066 ms, 0.094 ms and
0.291 ms, all below 1 ms with zero cache misses. The preceding executable/raster
benchmark is retained as intermediate evidence. These are local measured
files, not latency guarantees for every deployment or cache working set.

The accepted coherent-metadata/one-second-resolution assumptions still apply.
The helper provides bounded point-in-time observations, not arbitrary-writer
snapshot isolation or new path authority. Full sanity and restarted endpoint/
binary identity acceptance remain separate gates. Raster/virtual/directory
closure, scientific cache semantics and other inventory findings remain OPEN.
