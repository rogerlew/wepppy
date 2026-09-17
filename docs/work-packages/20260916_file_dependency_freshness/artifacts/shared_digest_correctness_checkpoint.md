# Shared ordinary-file digest correctness checkpoint

Independent reviewer: `freshness_correctness`, 2026-09-17 UTC. Reviewed the
shared-digest checkpoint and final canonical section, both actual callers,
their current owner contracts/tests, the admission ADR and retained actual-call
baseline probes. Starting revision: `dbec83d30`, with prior implementation waves
in the working tree. No production implementation edits made by this reviewer.

**Verdict: PASS for the two-consumer checkpoint. No blocking design finding.**

## Rationale and owner contracts

The two real baseline failures justify one owned ordinary-file digest helper:
`schema_digest_baseline_probe.json` shows an obsolete export SHA after a real
equal-size/restored-time rewrite. `registry_digest_baseline_probe.json` records
1,000 real rewrite pairs, 782 identical metadata versions and 452 obsolete
digests from the actual executable helper. No binary execution or named project
mutation was used. This is stronger evidence than similarity between cache keys.

The amended checkpoint correctly cites `rq-controller-state-contract.md` for
output trust metadata, including `size_bytes` and `sha256`; the broader agent API
contract does not itself define those artifact fields. The project-owned config
contract already defines executable byte digests as provider identity. The new
shared contract fixes digest conformance without changing those public shapes,
provider selection, executable role order, registry revision rules or project
creation's stale-schema behavior.

Leaving the specialized post-fire no-follow helper unchanged is appropriate.
This helper is ordinary-file byte identity, not run authorization, containment,
no-follow admission, raster closure or a persisted semantic signature. The
initial two callers require readable regular files; no directory-backed raster
compatibility branch is needed or claimed here.

## Required implementation properties

- Preserve SHA-256 lowercase hex output and the existing public response and
  provider identity strings. Same readable bytes after metadata churn retain
  the same digest, while changed bytes with preserved size/mtime are reverified.
- Retain the accepted full version key: absolute path, device, inode, size,
  nanosecond mtime and ctime. Open and check access plus descriptor/path agreement
  on every call, including settled cache hits. Caller containment, permitted
  symlinks and executable read/execute checks remain separate and mandatory.
- Keep both LRUs bounded at 512. During the first one-second monotonic observation
  interval, hash uncached. The first mature lookup must freshly hash before
  admission. Include observation generation in the digest key so eviction cannot
  resurrect an earlier digest. Failed reads must not admit digest results.
- `use_cache=False` must actually read verified bytes, independently of a warm
  digest entry. Bound content consumption to captured size plus one, reject
  observed descriptor/path/byte-count drift, and preserve explicit filesystem
  failures. Do not create a generic fallback digest or hide an unreadable file.
- The export wrapper's supplied size/mtime are consistency expectations. As now
  clarified in the canonical/checkpoint text, validate them against the verified
  observation or before and after the helper; a precheck alone leaves a race
  producing old size metadata beside a newer digest. Mismatch must raise into
  the existing best-effort discovery omission boundary.
- Keep registry `is_file` and read/execute checks and its `RegistryError`
  translation. An unusable binary invalidates availability atomically; never
  silently drop only that provider entry. No file writes or chmod are needed.

## Valid states and compatibility

Empty regular files retain their real empty SHA. Missing/unreadable exports
remain absent from discovery through the existing boundary; an otherwise valid
empty artifact remains distinguishable from absence. Missing/nonregular or
non-executable binary roles remain unavailable under their current error
contract. Permission loss after a previously successful warm read must still
fail. Allowed symlinks continue to resolve normally, with every access subject
to the same caller checks.

No persisted cache or run schema is migrated. Removing private cache variables
is safe after checking test seams; it does not authorize removing public caller
helpers. Ordinary unchanged inputs must remain valid, including legacy export
records whose existing provenance handling remains outside this hash change.
Point-in-time reads and the ADR's coherent metadata-on-open/at-most-one-second
timestamp-quantum assumptions remain explicit limits, not arbitrary concurrent
writer snapshot isolation.

## Required evidence and residual risks

Run actual caller regressions for both baselines and verify public propagation:
current export SHA/size with omission on expectation mismatch, and changed
executable identity through the provider/registry revision. Include real-file
growth/truncation/replacement, missing/access failure, empty input, symlink and
unchanged-content cases. A narrow hook can schedule an expectation-to-hash
interleaving, but must leave real file reads and comparisons intact.

Use deterministic monotonic-clock control for admission/eviction branch tests;
also rerun the original real rapid-rewrite acceptance without sleeps or mocked
stat timestamps. Demonstrate fresh first admission, observation-LRU eviction
without old-entry resurrection, failure without cache admission and zero
settled warm content reads. Settled performance claims apply to a resident
working set; bounded eviction legitimately incurs rehashing.

The existing cold 26.4 MB baseline and sub-millisecond settled lookup budget
are reasonable comparison gates, not proof of the unimplemented helper's cost.
Measure actual representative executable/export paths under canonical container
identities, including interleaved paths and caller overhead. Cold and one-second
admission reads must be reported separately from settled reuse.

Focused output-discovery/registry suites, public helper stub checks, full final
sanity, restarted endpoint/binary-identity acceptance and independent security
review remain required. Implementation must follow the standalone checkpoint
ancestor commit. This checkpoint closes no raster, report-cache, features-export
dependency-key or other open inventory finding.
