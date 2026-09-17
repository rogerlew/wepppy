# Required operation and state matrix

Proposed acceptance for content-dependent outputs; classify other consumers by
contract before applying these expectations. No tests have run for this package.

| Operation | Content-freshness expectation | Separate obligation |
| --- | --- | --- |
| Add/remove another hard link | Remain current if content/provenance unchanged | Inode/link metadata may change; access and race guards still apply |
| Create/remove a symlink pointing at the input | Target remains current | Do not weaken symlink rejection or containment rules |
| Chmod/chown or metadata-only touch | Content alone remains current | Access loss/ownership policy can independently make workflow unavailable |
| Same-byte atomic replacement or archive restore | Revalidate identity; remain content-current where contracted | Verify path/provenance and old/new schema rules |
| Changed bytes with changed size/time | Stale/rebuild as contracted | Never serve old output as current |
| Equal-size changed bytes with restored mtime | Still detect content change | Stat-only cache hit must not silently mask it |
| Repoint input symlink or path to different content | Reject or invalidate under existing policy | Content equality cannot override unauthorized path semantics |
| Change required sidecar/mask/metadata units | Invalidate affected output | Inventory dependencies beyond the main filename |
| SQLite commit, WAL change, checkpoint or backup | Evaluate coherent logical/byte snapshot per contract | No partial main/WAL view or writing to live DB just to inspect |
| Concurrent mutation during hash/read/publication | Retry boundedly or fail explicitly | No inconsistent accepted snapshot; preserve previous acceptance |
| Delete/unreadable/truncated required input | Explicit unavailable/stale outcome | No silent fallback or digest of empty substitute |
| Change model settings/source identity/tool version | Invalidate where contracted | Equal file bytes do not imply equal scientific meaning |
| Byte changes with equal parsed values | Consumer-specific decision | No blanket semantic equivalence policy |

Cover never-used optional state, present-empty state, populated state, supported
legacy signatures, missing required state and malformed/hostile records.
Keep tests on real filesystem operations for every changed boundary; mock-only
stat tuples do not prove the hard-link/race contract. Use the actual container
uid/gid, mounts and filesystem for live acceptance. Record NFS/local differences
where the supported workflow crosses them; do not assume timestamp granularity.

Measure cold hashing and repeated warm status reads using representative climate,
large raster and SQLite artifacts before choosing optimization. Record bytes
read, cache hit/revalidation behavior and elapsed latency. Set explicit per-path
budgets from the measured baseline before implementation; do not invent a global
latency threshold. Verify cached hashes against replacement and restored-mtime
cases under the actual producer/concurrency contract.
