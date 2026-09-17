# A-S01 archive directory metadata security checkpoint

**PASS for the refined bounded contract checkpoint.** No archive implementation
has been reviewed or approved. The actual failing roundtrip and A-S01 integration
finding remain in `archive_attempt_permissions_security_review.md` and its
linked probe. Reviewer: `freshness_security`; read-only code/contract assessment.

The amendment to the artifact observability standard and
`archive_directory_contract_decision.md` address the demonstrated loss at both
ends: new archives record traversed ordinary directories, and restoration
establishes recorded private ancestry before copying files. Final mode restore
runs deepest-first, allowing the restoring owner to populate read-only
directories without broadening recorded group/other access. This is the
smallest compatible shared correction; a restore-only chmod cannot recover
metadata the current writer never emits.

The refined reader rules are appropriate: validate the member/path and directory
mode inventory before destructive removal; recognize explicit UNIX directory
metadata even for mode0000; accept identical duplicate records but reject
conflicting modes for the same resolved directory before mutation; preserve
working-directory root mode regardless of a root-resolving entry. ZIP member
order cannot defer private ancestor protection until after a payload write.
Required directory-mode failures remain explicit rather than falsely certifying
parity. These rules do not authorize a new symlink, owner/group or ACL restore
mechanism, or weaken existing path validation/exclusions.

Legacy archives without usable directory mode metadata retain the previous
umask behavior. This is an honest compatibility limit, not recovered historical
privacy. Older readers may ignore the additive records; rollback documentation
must not promise they preserve private modes. Keep normal file handling and
archive naming/interfaces unchanged. Empty directory retention is consistent
with recording actual traversed ordinary folders; it must not start following
directory symlinks that the current walker excludes.

Implementation acceptance must exercise actual canonical archive and restore,
not fabricated mode-only assertions: private0700 and ordinary0750 folders,
nested readonly/mode0000 directories, empty directories, unsorted records,
identical/conflicting duplicates, root records, legacy ZIPs, mode-application
failure and existing traversal/symlink rejection. Observe private ancestor modes
at the first payload write, and assert final file bytes/modes. Supported
service UID/GID and normal browse/archive/restore remain final runtime gates.
Do not delete failed candidates, add attempt-path allowlists, hide records or
infer modes from current project contents to make the tests pass.

No unresolved medium/high design finding remains in this checkpoint. A-S01
itself closes only after implementation and actual producer roundtrip evidence;
the canonical ZIP's existing access policy and unrelated archive hardening are
outside this correction.

Reviewed SHA-256 values:

```text
artifact-observability-standard.md 0470093fe1aa4a143cab2d7f84051d9f1e4e910f7aabe866d3fe41a7b1b72245
archive_directory_contract_decision.md 1f5e8b952996b5987e4c1d0dfd7031c7b20a81b7e6d9921b7ec8ecc245a75171
```
