# Security review: catalog contention and stateless WBT

## Metadata

- Package: `20261109_culvert_catalog_contention`.
- Independent reviewer: `culvert_review`, 2026-11-09; root retained this artifact
  from the review findings and executable probes in [review.md](../review.md).
- Scope: catalog acquisition, WBT subprocess invocation, bundled-plugin options,
  Python process containment and explicit configuration publication.
- Source/build identity: `wbt-release-provenance.json` retained in the incident
  evidence directory; installed main SHA-256
  `28208e075a51f37d254a51b2a9f27c0ef7e5f273344c8665a0749b4714766777`.
- Related correctness review: [correctness-review.md](correctness-review.md).

## Security triage decision

Impact: high, because the expanded repair changes worker subprocess and filesystem
publication boundaries. Dedicated review required. Deployment is forest/Linux;
normal runtime uid1000/gid993/umask0022 is retained. Installation administrators
control executable/default paths; model jobs do not gain configuration-write
privileges. Environment-carried plugin options contain runtime options, not secrets.
No auth, scope, CSRF, queue edges, network egress or privilege changes.

## Findings

| ID | Severity | Surface | Evidence and resolution | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | Medium | Settings ownership/group | Real CLI initially changed1000:4 to creator identity; preserve uid/gid before publication or fail explicitly | Resolved |
| SEC-02 | Medium | Settings symlink | Initial replacement removed link; resolve target and publish beside it, retaining link | Resolved |
| SEC-03 | Medium | Temporary accessibility | Create mode0600 before bytes; empty probe preserves new-file umask/default ACL | Resolved |
| SEC-04 | Medium | Permission metadata | Preserve mode, Linux ACL and xattrs; direct named-ACL/user-xattr probes passed | Resolved |

## Surface checks

- Valid absent settings use existing defaults; malformed/unreadable settings fail
  explicitly. Readonly installations execute tools without writes. Supported
  Rust settings lacking Python-only `raise_on_error` remain valid.
- Subprocesses use argument arrays, absolute executable paths and per-child cwd;
  no shell interpolation or parent cwd mutation. Packaged wrapper now shares the
  established timeout/cancellation/reaping implementation; plugin failures propagate.
- Runtime configuration remains process-local, with explicit child propagation.
  All 25 installed bundled plugins were rebuilt and hash-verified with dispatcher.
- Atomic admin publication preserves symlink target and permissions. Metadata
  preservation failure aborts before replacement; post-rename directory-fsync
  failure may report a committed update and is documented. Concurrent admin
  read-modify-write commands are not advertised as transactional.
- Linux xattr FFI uses live descriptors and sized buffers. Kernel errors propagate;
  zero-length attribute growth is checked before copying. No unsafe-buffer issue
  identified by independent review.
- No new dependency, daemon, privilege or coordination protocol. Catalog owner
  fencing and stale-wrapper rejection remain; retry surrounds acquisition only.
- Live test credentials are short-lived, scoped and held in mode0600 temporary
  files. Payloads/private responses are excluded from repository artifacts.
- Prior runtime binaries/settings/plugins are retained for forest rollback.

## Validation and verdict

Independent real CLI probes preserved uid/gid1000:4, mode0640, symlink, named ACL
and user xattr; umask027 creates0640; no temporary residue. Worker-identity tests
cover readonly/absent/corrupt settings, permission failures, real parallel outputs,
plugin propagation and subprocess cleanup. 207 Rust and 23 Python tests pass.

Security gate: pass for forest/Linux; unresolved high0/medium0/low0. Full batch
artifact acceptance remains a separate correctness gate. Windows/macOS metadata
parity and old external prebuilt plugins are unverified and are excluded from
this installation recommendation. No production rollout is authorized here.
