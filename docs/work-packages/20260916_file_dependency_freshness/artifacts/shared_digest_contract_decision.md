# Shared ordinary-file digest checkpoint

Starting revision `dbec83d30`; existing implementation waves remain in the
working tree. Owner authority: execute the repository freshness audit/fix.
Canonical authority: file-dependency-freshness-contract Shared ordinary-file
digest reuse, project-owned-config-contract binary identity and
rq-controller-state-contract output artifact SHA metadata and
rq-engine-agent-api-contract access/response surfaces. No model parameter changes.

## Concrete evidence and proposed smallest shared scope

Actual schema_defaults `_sha256_file` returns the prior digest after a real
same-size/restored-time rewrite: schema_digest_baseline_probe.py/.json. The
project-config executable helper uses a separate unbounded metadata hash cache
with no coherent-read checks. Its full metadata key has the same timestamp
collision vulnerability already reproduced by the retained rapid rewrite probes;
the actual callable probe now confirms 452 stale digests among 1,000 rapid
rewrites (782 full-metadata collisions). See registry_digest_baseline_probe.json;
no executable was run. Reproduce the actual callable after the fix.

Add `wepppy/all_your_base/file_digest.py` with `sha256_file(path, use_cache=True)`.
It verifies ordinary regular-file reads, hashes no more than captured size+1,
and uses the reviewed 1-second observation / 512-entry LRU admission policy.
Use it only in these two confirmed compatible byte-digest consumers initially.
Do not move post-fire's specialized no-follow implementation in this wave or
create raster traversal here. An uncached mode supports explicit bounded
verification and testing; normal calls still open/check access before reuse.
This small owned utility consolidates identical byte-hash behavior; it is not a
universal persisted signature, a semantic fingerprint or a path authorization API.

## Compatibility and states

- Existing response JSON, digest format and executable identity strings remain
  unchanged; no run schema/migration or cache-index mutation.
- Missing/unreadable export retains the existing discovery omission boundary.
  A supplied size/mtime mismatch must raise OSError into that boundary; check
  expectations against the read observation or before and after the helper to
  prevent drift after a wrapper-only precheck.
- Executables retain the existing is_file and read/execute checks, plus the
  existing RegistryError translation on filesystem failures. No chmod/write.
- Empty regular files hash normally. Nonregular files retain caller validation;
  do not claim this helper supports directory-backed rasters or virtual files.
- Same bytes after touch/link/chmod/replacement have the same digest if access
  permits; changed bytes with preserved size/mtime must change the digest.
- Never turn cache access, hashing or invalid metadata failures into success.
  Supported coherent POSIX/NFS metadata and timestamp-resolution assumptions
  remain exactly those in the accepted admission ADR.
- Removing the old private caches does not remove a public API. Update tests that
  explicitly reset these private caches to the owned helper's test seams.

## Budgets, regressions and scope limits

Reuse the existing actual 26.4 MB cold digest baseline and <1 ms settled lookup
budget; require zero settled warm content reads, actual rapid rewrite probes,
cache eviction/failed-read cases and replaced-during-read rejection. Measure
representative executable and export files under canonical container identities.
The warmed cache must remain bounded under interleaved paths. Actual caller
regressions must exercise the old failure and preserve error translation/access
checks. Run affected schema discovery and registry suites, stub checks for the
new public helper, full sanity after final edits, and restarted endpoint/binary
identity acceptance. Scope does not close features-export dependency keys,
raster closure, report caches or other inventory findings.

Independent correctness/security contract reviews and a docs-only ancestor
checkpoint are required before implementation. Existing numerical defaults and
all authorization/selection behavior remain unchanged.
