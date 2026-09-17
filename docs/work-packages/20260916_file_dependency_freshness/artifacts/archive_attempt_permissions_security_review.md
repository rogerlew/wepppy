# Canonical archive directory permissions discovery

**A-S01, medium, verified closed by the bounded implementation after-probe.**
The original finding below was that canonical roundtrip loses private attempt
directory permissions. This is an integration gate for the package's new artifact
producers. The underlying archive omission predates this package; the changed
workflows nevertheless depend on private directories to contain readable native
intermediates. At discovery, the scoped Geneva generation review remained PASS,
but archive permission parity and whole-package runtime acceptance did not pass.
See `archive_directory_implementation_security_review.md` for the accepted
checkpoint and actual successful producer roundtrip. Whole-package runtime
acceptance remains a separate gate.

## Actual evidence

`archive_attempt_permissions_security_probe.py/.json/.log`: **1 failed in
9.31 s**, using the actual Geneva `_Attempt` writer and canonical `archive_rq`
and `restore_archive_rq` on a disposable project. Only job/status/Redis transport
is supplied through the existing `ArchiveRuntime`; filesystem, ZIP, lifecycle
guard and restore behavior are real. UID 1000; no named project is mutated.

| Record | Before | After restore |
| --- | --- | --- |
| `geneva/cache_attempts` | 0700 | 0755 |
| Failed attempt leaf | 0700 | 0755 |
| Its partial candidate | 0644 | 0644 |
| Its status | 0600 | 0600 |
| Separate ordinary directory control | 0750 | 0755 |
| Its private file control | 0600 | 0600 |

All file bytes and file modes survive. The ZIP contains **no directory entries**.
`archive_rq` iterates files only (`project_rq_archive.py:299`); restore creates
implicit parents with default mkdir behavior. Even an explicit directory member
would hit mkdir/continue without restoring its mode (`:412`). Consequently a
restore-only chmod addition cannot recover modes absent from the archive.

The restored 0644 failed candidate no longer has the producer's private ancestor
barrier. This establishes POSIX mode broadening, not a demonstrated remote or
cross-user disclosure. Project browse/download authorization remains unchanged.
The existing archive ZIP itself uses its normal archive access policy; this
review does not claim a new ZIP permission leak or redesign that policy.

The cross-wave dependency is concrete: Geneva private attempts protect native
and JSON candidates; report `_CacheBuild` uses directory permissions derived
from an existing restricted output to protect native internal staging; CLI
attempts are 0700, although its explicitly 0600 payloads retain that individual
file barrier after this roundtrip. Review actual retained payload modes per
producer rather than declaring every restored file equally exposed.

## Smallest compatible follow-up

Ratify a bounded canonical project archive directory-metadata checkpoint before
changing shared archive code. New archives need explicit ordinary directory
entries with recorded permission semantics; restoration must establish required
private ancestry before writing its payloads and retain the intended final
directory modes. Applying restrictions only after extraction leaves a readable
intermediate window. Handle read-only directories without preventing the restore
from populating them, and do not silently report success when a required privacy
mode could not be applied.

Keep current project lifecycle locks, path validation, exclusions, file member
semantics, identity/group ownership model and error/status authority. Do not
create symlinks from ZIP metadata or begin traversing directory symlinks merely
to collect directory entries. No new archive service, permission framework,
hidden snapshot or artifact exclusion is needed. Preserve useful failed work.

Distinguish legacy archives without directory metadata: their original modes
cannot be inferred. Keep the documented legacy behavior without inventing
historical provenance, or ratify a separately explicit legacy policy. State the
new archive format/reader compatibility and permission-bit interpretation,
including the treatment of unsupported metadata, in the checkpoint. Do not
silently extend this correction to ownership, ACL restoration or generalized
archive hardening.

Required evidence: actual new archive roundtrip for private and ordinary
directories, file-mode/byte parity, empty directories, readonly parent layouts,
legacy ZIPs, existing symlink/path validation and required-mode failure. Repeat
the new producer's normal browse/archive/restore workflow under supported service
identities. Original failing evidence must remain retained. No source or tests
were edited by this review, and no new contract or implementation is approved by
this discovery artifact alone.
