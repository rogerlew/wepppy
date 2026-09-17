# NoDb hydration implementation correctness review

Reviewer: independent `freshness_correctness`, 2026-09-17 UTC. Reviewed the
working-tree NoDb wave after checkpoint
`4e000950a49ac1ae0dca85aed1c36abcda3c9de1`: `base.py`, `_read_retry.py` and its
stub, `test_hydration_snapshot.py`, and the boundary-characterization fixture
changes. No implementation edits were made by this reviewer.

**Verdict: PASS for the bounded implementation; no major correctness finding.**
The two scoped regression gaps below are now resolved and independently reviewed.
Runtime delivery and package closeout remain open.

## Correctness assessment

Both disk loaders call `read_text_snapshot`, carry its text/stat pair through
decoding, and assign `_nodb_mtime/_nodb_size` from that same descriptor generation.
There is no later pathname stat that can label payload A with replacement B's
version. The retained two-loader regression schedules a real atomic replacement
during decode and confirms A's original mtime and a cache-version mismatch.

The helper keeps the existing default text open/decoding/newline semantics.
Its descriptor comparison includes device, inode, byte size and nanosecond mtime;
it does not compare character count with byte size. Unicode coverage exercises
that distinction. Omitting ctime is deliberate: removing the old pathname during
atomic replacement changes the old inode's ctime without changing its complete
bytes. A complete earlier A/A observation remains valid under the existing
atomic-writer contract.

An observable in-place modification raises `OSError(ESTALE, ..., path)` through
the existing `_call` boundary. The scoped test retries the entire read transaction
and returns the newer complete payload; outside the initial-read scope it raises
immediately. Optional ENOENT and the original permission-error object are
preserved. Decode errors remain outside the retry helper, preserving existing
malformed-JSON behavior.

The NoDb writer, lock ownership, atomic replace, monotonic mtime, Redis lookup,
cache comparison, detached logging and post-commit mirror paths are unchanged.
Redis may briefly receive the complete older A payload after a concurrent B
publication, but A retains A's signature and normal Redis cache validation rejects
it against B. The fix does not create a new schema or content-cache policy.

## Tests and resolved findings

`nodb_focused_revision2.log` records **155 passed** after correcting the test OS
stub to include `fstat`. `nodb_stubtest.log` reports no issues for
`wepppy.nodb._read_retry`. Updating the cold optional-disappearance fixture to
inject absence at open is appropriate: its previous post-decode pathname-stat
boundary no longer exists. Singleton/Redis absence tests retain their original
signature boundary.

Follow-up `nodb_review_regressions.log` records **76 passed**, covering the
hydration snapshot and boundary-characterization modules after both requested
regressions were added. This reviewer checked their actual filesystem scheduling,
lock/write path and assertions; no production implementation changed in this
follow-up.

| ID | Severity | Disposition and evidence |
| --- | --- | --- |
| NODBC-01 | Low, resolved | `test_decode_time_replacement_rejects_subsequent_stale_dump` is parameterized for both loaders. A real atomic replace during decode leaves observed A; a normal `observed.locked()` mutation attempts to persist C and raises `NoDbStaleWriteError`. Exact replacement B bytes remain unchanged. |
| NODBC-02 | Low, resolved | `test_open_descriptor_replacement_preserves_complete_old_snapshot` now replaces the path inside `ReplacingReader.read`, after old text is read and between the helper's two descriptor stats. It verifies complete Unicode A with A's inode/size/mtime while the pathname contains B. |

No scoped correctness finding remains open.
No broad refactor, new dependency, lock or NoDb signature expansion is justified
by this wave. Uncoordinated in-place writers that restore/collide every observed
metadata field remain outside the cooperative atomic-writer guarantee; this
change must not be described as solving that separate inventory concern.

## Related first-wave conformance

The canonical freshness contract now distinguishes detected generation changes
from a coherent point-in-time observation that overlaps a later same-quantum
write. `test_complete_uncached_read_has_a_point_in_time` explicitly characterizes
that case while checking the next observation and avoiding stale cache reuse.
That resolves the wording/test concern in `first_wave_correctness_followup.md`;
it does not permit hybrid generations or waive first-wave final validation.

Substantive full-suite sanity, rebuilt/restarted services, real UI/RQ/WEPP and
archive/restore acceptance, final security review and remaining consumer waves
are still required by the active package. This review claims no live acceptance.
