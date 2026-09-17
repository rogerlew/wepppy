# First-wave correctness follow-up after cache admission guard

Independent reviewer: `freshness_correctness`, 2026-09-17 UTC. Amendment ancestor
`0fe02dc0fd1182d217d855d931f6c7c0e53ce9e7` verified. This supplements, rather than
erases, the initial failed review and retained failing test logs.

## Finding disposition

- **FWC-01, stale cache reuse: corrected for the demonstrated case.** The guard
  hashes uncached during its monotonic observation interval. Mature cache keys
  include the observation timestamp, so eviction/re-observation cannot resurrect
  an older cached digest. `ctime_probe_after_admission.json` records 933 full-stat
  collisions on `/tmp` and 33 on repository storage, with **zero stale digests**.
  The NFS case again had zero collisions and zero stale digests in 1,000 attempts.
  No sleeps or mocked stat fields were added to that probe.
- **FWC-02, M1 pre-run metadata churn: code corrected.** `verified_active` pins
  the generation observed when the new run starts. Publication compares that
  capture rather than historical acceptance timestamps. The real upload/model
  test now hard-links a normalized input before execution. Final revised-suite
  success and during-build mutation rejection remain required evidence.
- **FWC-03, route error translation: code corrected.** Expected `open_local`
  `RainfallError` now becomes `changed_file`/409. Final route regressions remain
  part of the primary agent's validation.
- **FWC-04, source hashing under finalization locks: ordinary-source cold reads
  removed.** `sources(content=False)` retains strict metadata snapshots for
  `_current_authority` and upload finalization, while execution-boundary full
  digests remain outside the lock. Existing engine/tool identity reads are
  unchanged obligations.

The hash loop now additionally rejects both growth and a final byte count that
differs from the captured size, alongside descriptor/path identity checks.

## Revision-3 single-block mutation failure

`first_wave_focused_revision3.log` retains a failure in which the six-byte file
contained `before` when the read copied all bytes. The controlled hash-update
hook then wrote `AFTER!` before the final stat checks. Both timestamp values
collided, so the call returned the digest of `before` rather than an exception.

This observation is **not a mixed-generation digest and not stale cache reuse**.
All returned bytes coexisted as the complete old file at a point during the
call. A concurrent operation can validly observe that old generation; no read
can promise that a writer will not modify a file immediately after its last
byte is read. The guard leaves this digest uncached, so the next observation
rehashes the new bytes.

The canonical sentence “Replacement or concurrent mutation fails explicitly”
is broader than the actual observation guarantee. Clarify that detected
generation changes fail and that a read overlapping a later write may return
a coherent old-generation observation; do not claim detection of every write
after the final byte. This clarification does **not** authorize accepting mixed
generations or suppressing observable changes.

The smallest defensible test treatment is to retain the original failed log,
exercise the metadata-change rejection branch with a real deterministic mtime
change (as now implemented), and separately characterize the overlapping
single-block case: either reject or return a complete old/new generation,
never cache it during observation, and read the new digest on the next call.
Do not add a sleep merely to make the original timestamp assumption true.

## Multi-chunk probe and limits

`first_wave_mixed_read_probe.py` performs a real 2 MiB streaming read, overwrites
the whole file immediately after the first 1 MiB block, then continues reading.
An undetected read would combine an old prefix and new suffix, rather than any
complete before/after generation. The hash-update hook controls scheduling;
filesystem metadata and byte reads are real.

The retained `first_wave_mixed_read_probe.json` rejected **150/150** such reads
on `/tmp` and **150/150** on repository storage with `changed_source`; no hybrid
digest was returned. This is bounded evidence only. It does not prove immunity
to arbitrary writers, all scheduling, NFS incoherence or hidden filesystem
versions. The six-byte observation alone does not justify a new locking,
snapshot-copy, watcher or writer protocol.

## Current review status

The admission-guard implementation conforms to its reviewed strategy, and the
demonstrated stale-cache blocker is resolved. Update the observation wording
above and retain the short-read characterization before final conformance
sign-off. Final focused/broad test outcomes, settled warm benchmarks after all
changes, independent security sign-off, restarted UI/RQ/WEPP and archive/restore
acceptance remain open. This follow-up does not close the package or its
non-postfire findings.
