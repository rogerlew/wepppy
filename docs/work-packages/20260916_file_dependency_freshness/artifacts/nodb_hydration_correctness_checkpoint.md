# NoDb hydration conformance correctness checkpoint

Independent reviewer: `freshness_correctness`, 2026-09-17 UTC. Reviewed
`artifacts/nodb_hydration_conformance.md`, both disk hydration paths in
`wepppy/nodb/base.py`, `_read_retry.py`, the retained SEC-M1-01 reproduction,
and NoDb boundary/initial-read retry tests before NoDb implementation edits.

**Verdict: PASS as an unchanged-contract conformance correction.**
The existing NoDb persistence/concurrency contract requires disk-authoritative
hydration, signature-based cache rejection, stale-write rejection and atomic
replacement. Returning generation A's decoded payload with replacement B's
mtime/size violates those requirements. The proposed descriptor-bound text/stat
read restores them without changing the persisted schema, writer protocol or
scientific identity policy.

## Required implementation behavior

1. Read text and obtain its metadata from one descriptor. Carry that metadata
   through decoding and assign `_nodb_mtime/_nodb_size` from it. Neither loader
   may tag decoded text with a later pathname stat.
2. A concurrent atomic replacement may leave a complete earlier A payload with
   A's own signature. That is a valid read observation; subsequent cache checks
   and dump compare against the current pathname and reject/refresh A as usual.
   Do not add mandatory post-decode pathname equality to disguise this race.
3. Compare descriptor identity/size/timestamps around the read and reject
   observable in-place mutation with `ESTALE` through the existing scoped retry
   wrapper. Preserve explicit failure outside that scope. These checks do not
   claim detection of all metadata-quantum collisions by uncoordinated writers;
   cooperative NoDb writers already publish atomic immutable generations.
4. Preserve default text decoding/newline behavior. Python character count is
   not equivalent to `st_size` for UTF-8 or newline translation; do not reject
   valid non-ASCII JSON by comparing those different units.
5. Keep Redis lookup/validation, singleton refresh, detached logging semantics,
   lock ownership, monotonic writer mtime, permissions/fsync, commit outcome and
   best-effort mirrors unchanged. No content-digest cache is needed here.

## Valid states and validation

| State | Required outcome |
| --- | --- |
| Ordinary valid disk JSON | Decode it and retain the read descriptor's signature |
| Optional absence at open | `None` immediately under existing policy |
| Required ENOENT / ESTALE | Preserve errno and bounded initial-read retries; no unscoped retry |
| Complete old generation replaced during decode | Return old payload with old signature; cache mismatch and stale-write rejection remain effective |
| Observable in-place mutation during read | Explicit ESTALE; retry only within initial-read scope |
| Empty/malformed JSON | Preserve existing decode failure; never fabricate an empty controller |
| Existing legacy fields / Unicode text | Preserve decoding and compatibility handling |

Convert the retained real `os.replace` reproduction into both-loader regressions.
Assert values **and** matching old signature, then prove cache mismatch and the
usual stale-write rejection against the replacement. Include scoped ESTALE
recovery and failure/optional absence. Use real descriptors/files at the changed
boundary; narrow hooks may schedule the competing write.

`test_optional_disappearance_at_signature_does_not_retry` currently injects
absence through a pathname stat. Its cold-loader case targets the obsolete
post-decode stat and must be revised to a real pre-open absence case or an
explicit earlier-complete-generation outcome. Do not add an unnecessary later
pathname stat just to preserve that implementation-shaped fixture. Singleton
and Redis cache-path absence behavior remains required.

Targeted NoDb, retry and stub gates plus substantive full sanity remain required.
No runtime approval is implied by this design checkpoint. The change does not
resolve unrelated NoDb out-of-band timestamp-preserving edits, Redis version
precision, or the broader package's open freshness consumers.
