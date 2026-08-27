# WP10 Security and Data-Integrity Review

**Date**: 2026-08-26
**Scope**: project-config lifecycle guard, fork, archive, restore, ZIP members
**Disposition**: accepted; no unresolved high-severity finding

## Review

WP10 does not change route authorization, enqueue permissions, archive download
authorization, or public/read-only mutation policy. Those existing boundaries
remain authoritative. The new code operates only after the existing lifecycle
job begins and uses the already established project-scoped amendment lock.

The archive member allowlist is tightened: `.config-amendment.lock` and
`.config-amendment.pending.json` are transaction machinery and are excluded
both while creating archives and while collecting restore members. Restore
keeps the active lock inode in place during destructive replacement, preventing
a concurrent updater from acquiring a newly recreated lock path. Existing ZIP
integrity, traversal containment, disk-space, and NoDb-lock checks remain.

The lifecycle guard performs deterministic journal recovery from recorded
bytes; it does not re-resolve registry values. Config and manifest contents are
copied byte-for-byte and remain subject to the previously accepted project
config materialization scanner. Tests inspect archive membership and exact
bytes, exercise a mid-transaction recovery, and prove a concurrent amendment
waits until the lifecycle window exits. The recovered archive also passes the
canonical redacted `scan_archive` materialization gate.

## Authorization Disposition

Read-only and public state still cannot enqueue or execute configuration
updates. WP10 adds no mutation route. Existing WP08 owner/Admin/Root enqueue and
worker reauthorization tests remain the direct evidence for this boundary;
WP10's lifecycle operations preserve existing fork/archive/restore permissions.
