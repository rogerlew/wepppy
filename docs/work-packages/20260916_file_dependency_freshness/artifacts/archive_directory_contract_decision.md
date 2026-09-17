# A-S01 retained-attempt archive permission checkpoint

Status: proposed bounded correction; independent reviews pending. No archive
production edits yet. The authoritative amendment is the artifact observability
standard's "Project archive directory metadata" section.

Actual canonical archive/restore preserves files and file modes but emits no
ZIP directory entries. A real failed Geneva attempt0700 and ordinary0750
folder both restore0755 under the service umask. This breaks directory privacy
for the new retained-attempt producers. A restore-only chmod fix cannot recover
metadata never recorded. No remote-disclosure claim is made.

New archives add ZIP directory entries for existing traversed ordinary folders,
including empty folders, while preserving exclusions, symlink-directory handling,
root ownership/mode, file authority and archive interfaces. Restoration validates
members first, establishes recorded ancestry before payload writes, temporarily
adds only owner traversal/write access needed for extraction, then reapplies
recorded modes deepest-first. Directory chmod failures are explicit. Existing
file permissions/ownership logic remains. Do not add another manifest store,
archive format, service, dependency or special attempt-path allowlist.

Legacy ZIPs without directory metadata retain existing umask-derived behavior.
This is an additive archive schema change: test old archives, arbitrary member
order, nested0700/0750/readonly directories, empty folders, existing exclusions,
symlink traversal rejection and failure evidence. Test actual canonical archive
and restore under ordinary service UID/GID, asserting archived entries, restored
bytes/modes and private ancestry at the first payload write. No inferred modes
for old archives and no silent chmod error suppression in the new directory path.
Existing archive tests and full package runtime/browser/archive gates remain.

Review precision: explicit UNIX directory type in external attributes identifies
mode metadata, including permission0000. Missing metadata remains legacy.
Conflicting explicit modes for one resolved directory reject before destructive
restore; identical duplicates are accepted. No ZIP entry authorizes chmod of the
working-directory root, and existing member/path rejection remains unchanged.
