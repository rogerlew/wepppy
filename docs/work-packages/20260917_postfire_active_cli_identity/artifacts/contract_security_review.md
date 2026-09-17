# Active CLI identity contract security review

Reviewer: independent `active_cli_security` agent. Review started
2026-09-17 18:30 UTC against implementation
`0b5d063d3947e8a2ed56f7d9b3f73a7fd6ac7cc5`. Production files were read only.

## Findings and disposition

**PASS for the contract checkpoint, 2026-09-17 18:33 UTC. No unresolved medium
or high findings. Implementation approval remains a separate final gate.**

- **Medium, SEC-01, closed: conflicting worker identity authority.**
  `wepppy/nodb/mods/postfire_debris_flow/docs/production_m1.md`,
  "File-content currentness refinement," says strict worker publication remains
  unchanged, while the proposed shared contract permits an active CLI exception.
  Inconsistent authority could allow either continued denial of valid work or an
  overly broad metadata waiver. Independently verified new explicit superseding
  amendments in `production_m1.md`, `production_m3.md` and
  `production_m3_runtime.md`, each linking the exact shared amendment and retaining
  all other source, owner, selection, SQLite and artifact guards. This resolves
  the conflict before implementation.

## Threat model and proposed boundary

The changed surface is active scientific-input identity during M1/M3 admission,
M3 source promotion/rebase, pre-publication verification and locked publication.
Run-local writers can change or replace files, create/remove links or change
selections while a worker runs. They must not publish results against different
input bytes or substitute a newer attempt's ownership. Authorization, routes,
CSRF, queue topology, remote acquisition and secrets are unchanged.

The proposed exception is appropriately narrow: only `files.active_cli` ctime
may differ. The same relative path, size and mtime, an existing valid admission
SHA-256, a fresh uncached coherent hash and all other source/selection identity
are required. New hash maps, when present, remain identical. A missing legacy
digest cannot be invented from the current file. Source preparation may promote
only its existing owned pointer/receipt boundary, not unrelated input changes.

`production.signature(strong=True)` bypasses the digest cache using
`_digest_version.__wrapped__`. That helper uses `rainfall_io.open_local`, which
walks directory components without following symlinks and opens a bounded regular
file descriptor. Device, inode, size, nanosecond mtime/ctime and byte count are
checked across the read and against the pathname. Strong signature checks the
path again after the read. The new comparator must bind the returned stat record to
its current source snapshot; a prior cache hit or a path-only digest is
insufficient. Preserve the same read failure behavior.

Result/predictor/dNBR artifact finalizers, SQLite/soil identity, owner and attempt
selection checks must retain strict semantics. Do not replace them with the
permissive accepted-result currentness comparator.

## Required implementation evidence

- Real hard-link creation and removal succeeds at each changed stage for
  otherwise valid M1/M3 inputs, including actual overlapping WEPP preparation.
- Equal-size changed bytes with restored mtime cannot obtain this exception.
  Missing/malformed old hashes, mismatched current hash maps, changed path,
  size/mtime, other-source ctime and selection/ownership changes reject.
- Real no-follow/regular-file tests and descriptor/path replacement or mutation
  during hashing fail closed. At least one regression must prove the hash is
  uncached even when a cached digest would incorrectly appear acceptable.
- Failed replacements retain the prior accepted state and browsable diagnostics;
  native worker acceptance follows service restart. Final security review checks
  the actual patch, test evidence and checkpoint ancestry before closeout.

## Residual risk and noninterference

This remains bounded before/after verification under existing filesystem trust,
not snapshot isolation against a privileged arbitrary writer. Hard-link churn
during the coherent read itself can still fail explicitly; stable ctime drift
outside that window must not block valid publication. A changed CLI is rehashed
inside finalization only for the exceptional path, so assess real CLI size and
lock duration during runtime acceptance. No general cache, locking, schema or
scientific policy change is authorized by this repair.

Documentation validation: scoped `wctl doc-lint` passed with no errors/warnings;
spelling normalization was previewed.
