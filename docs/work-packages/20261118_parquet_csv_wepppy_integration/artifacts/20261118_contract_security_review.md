# Independent M0 security review

Date: 2026-11-18 UTC. Reviewer: csv_contract_security (read-only agent).
Verdict: approve checkpoint design; no unresolved medium/high findings.
This is not implementation or deployment approval.

Reviewed integration contract hash:
`eb7cf64345dd7304d955a1798b1fb0d59dd5d53b5f32d3a1aaed047a102c620c`.
Subsequent correctness amendments expand bounded IPC headroom and document
operator-approved invalid-UTF8 rejection; final implementation review remains due.

Initial findings and disposition:

- Orphan lifetime: inherited flock alone cannot bound I/O waits. Resolved by
  independent native wall alarm and race-checked parent-death termination; locks
  remain until actual exit, including delayed kernel termination.
- Response ownership: background tasks miss error/range branches. Resolved by
  lifecycle ownership through final ASGI send, disconnect/cancellation/errors,
  serving deadline and full-response behavior without range semantics.
- Pre-header deadline: standalone180+180 exceeded shortest proxy timeout.
  Resolved by staging30+conversion120 and explicit heartbeat validation.
- Filter boundary: resolved by bounded versioned request and schema work in child.

Persistent slot inodes plus inherited open-file-description locks were directly
probed: parent close does not release the child's inherited lock, and child exit
does. Reclaim only after acquiring the slot; never LOCK_UN or unlink lock files.
Authorized shared-root symlinks and installed source provenance are preserved.
Transient deletion is explicitly operator-approved and narrowly scoped.

Dependency review:88 third-party crates,0 known audit vulnerabilities, retained
Chrono maintenance warning. ZSTD acceptance conditional on parity, hostile-frame,
resource and exact-image tests. Nonblocking checks: exercise inherited descriptor
above63 under RLIMIT_NOFILE64 and classify child SIGALRM explicitly (now504).
