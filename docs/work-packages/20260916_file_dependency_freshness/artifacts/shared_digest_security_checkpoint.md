# Shared ordinary-file digest security checkpoint

## Findings and disposition

**PASS for the proposed bounded checkpoint; no open scoped findings.** Review
date: 2026-09-17 UTC, working tree at `dbec83d30ec532cf05af199e31558992922f2305`.
Reviewed `shared_digest_contract_decision.md`, the canonical file-dependency
contract's **Shared ordinary-file digest reuse** section, the admission ADR,
the two actual consumers and their current domain contracts. No implementation
or test files were changed by this reviewer.

Two review precisions are resolved before implementation:

- The direct owner of output artifact `size_bytes`/`sha256` is
  `docs/schemas/rq-controller-state-contract.md` (downloadable artifact trust
  metadata); the RQ agent API contract supplies the route/access context.
  The checkpoint now names both.
- Supplied output size/mtime must match the verified read observation, or be
  checked before and after the helper. A wrapper-only precheck cannot prevent
  drift before the helper opens its file. The canonical and checkpoint text
  now state this explicitly.

## Concrete evidence and scope

`schema_defaults_routes._sha256_file` currently caches by resolved path, size
and mtime. `schema_digest_baseline_probe.py/.json` use a real same-size rewrite,
restore mtime and call that function again: it returns the previous digest
instead of the actual current bytes' SHA-256.

`config_builder.registry._executable_sha256` has an unbounded dictionary keyed
by resolved path, inode, size, mtime and ctime. The actual-callable
`registry_digest_baseline_probe.py/.json` record **1,000 iterations, 782 equal
metadata versions and 452 stale digests** in the canonical container. The
disposable fixture is readable/executable, but no binary is run. This supplies
consumer-specific evidence beyond merely inferring the same cache defect.

A small owned ordinary-file SHA-256 helper addresses both confirmed consumers
without changing the meaning of their digests. It is not a new scientific
fingerprint, persisted signature schema, dependency resolver or authorization
mechanism. Initial adoption is limited to these two functions. Post-fire's
component-wise no-follow opener and specialized exception contract remain
unchanged; the shared helper must not silently replace either.

## Authority, errors and valid-state behavior

Output discovery already requires a finished matching-run job, resolves its
artifact through `features_export.service.resolve_download_artifact_path`,
checks `is_file`, and independently verifies resolved run containment. Retain
all of those checks and the route's existing authorization. Directory-backed
rasters are not an accepted input to this artifact resolver; unlike the C01
case, the helper's regular-file scope does not narrow its valid domain.
Unavailability or supplied-metadata mismatch must reach the existing discovery
omission boundary, without returning a previous digest or rewriting metadata.

The registry currently checks `is_file` and `os.access(R_OK | X_OK)` before
digest lookup, then translates filesystem failures to `RegistryError`. Preserve
those checks on every call, including settled cache hits; the helper additionally
opens for read access on every call. A cached hash cannot authorize unreadable
or nonexecutable content. Keep binary selection and the ordered
`provider-v1:watershed=<sha256>:hillslope=<sha256>` identity unchanged. No chmod,
execution, provider mutation or deployment-path publication is authorized.

Empty regular files retain SHA-256 of empty bytes. Missing/read-denied files
retain explicit filesystem failure and consumer-specific translation. Existing
allowed symlinks remain allowed, and their access checks must not disappear
because cache keys use absolute/resolved paths. Same readable bytes retain
their digest after touch, hard-link creation, chmod or replacement. Changed
bytes with preserved size/mtime must not reuse a metadata-colliding digest.

## Cache and read assumptions

Use the accepted one-second monotonic observation interval and separate bounded
512-entry observation/digest LRUs. Newly observed versions hash uncached;
maturity admits a fresh hash. Observation eviction restarts verification, and
the observation-generation value must participate in digest reuse so an older
surviving entry cannot reappear after eviction. An uncached call must actually
verify bytes, not consult an existing digest.

Every call retains current read access and descriptor/path agreement, while
cold reads enforce captured-size-plus-one consumption and reject observable
growth, truncation, replacement or version drift. Failed reads supply no cached
digest and no fabricated empty value. Existing point-in-time read limits apply:
these checks are not arbitrary-writer snapshot isolation. The ADR assumes
coherent metadata on open and timestamp quanta no coarser than one second;
prior development probes do not establish every NFS deployment's behavior.

## Required implementation and acceptance evidence

Rerun both actual consumer probes after implementation. Keep the registry probe
on the real clock without sleeps or fabricated metadata; synthetic clocks are
appropriate only for cache-branch coverage. Exercise fresh admission, failed
read, replacement, eviction with interleaved paths, bounded capacity and zero
settled warm content reads. In particular, a surviving digest must not be
reused after its observation record was evicted.

Consumer regressions must preserve omission/RegistryError behavior, supplied
size/mtime coherence, allowed symlinks, readable/executable access checks and
unchanged response/identity formatting. Measure actual export and executable
files under the canonical runtime identity. Required public-helper stub checks,
affected suites, final full sanity and restarted endpoint/binary identity
acceptance remain outstanding at this checkpoint.

This pass does not close feature-export dependency semantics, raster/virtual/
directory closure, report caches or the package's other inventory findings.
