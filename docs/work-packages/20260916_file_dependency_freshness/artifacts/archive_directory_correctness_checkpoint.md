# A-S01 archive directory metadata correctness checkpoint

**PASS for the bounded contract checkpoint.** No archive implementation has
been reviewed. The retained canonical roundtrip establishes the defect without
speculating about remote disclosure: the real Geneva failed-attempt directories
change from0700 to0755, and an ordinary directory changes from0750 to0755, while
payload bytes and file modes survive. See
`archive_attempt_permissions_security_probe.json` and its script/log.

The shared correction belongs in `wepppy/rq/project_rq_archive.py`:
`archive_rq` currently walks ordinary directories but writes only files;
`restore_archive_rq` currently creates parent directories with the restoring
process's umask and applies only file modes. A restore-only change cannot
reconstruct the missing historical directory modes. Additive ordinary-directory
ZIP records plus mode-aware extraction are the smallest correction for all
retained-attempt producers; no producer-specific directory allowlist is needed.

The refined canonical rules are coherent and compatible:

- Emit entries only for directories actually traversed by the existing walker,
  including empty directories. Preserve exclusion pruning and the current
  non-following treatment of directory symlinks. The run root is not a member.
- Build and validate the complete member/mode inventory before destructive
  cleanup. Conflicting explicit modes for one resolved directory are invalid;
  identical duplicates do not change the result. Root-resolving entries cannot
  authorize a root chmod, and existing path checks remain in force.
- Prepare recorded ancestry before any payload extraction, independently of
  ZIP member order. Temporary access may add owner permissions only; group and
  other access must not exceed the recorded mode. Restore exact modes deepest
  first so read-only or mode0000 ancestors do not prevent completion beneath
  them. Required chmod failures remain explicit failures.
- Explicit UNIX directory type distinguishes real mode0000 metadata from
  missing metadata. Legacy archives and untyped directory records keep their
  prior umask behavior. No root mode, owner, group, ACL, file-authority or archive
  interface change is authorized. Historical privacy is not retroactively
  established for ZIPs that never recorded directory modes.

No medium/high design finding remains. Implementation acceptance must cover
actual canonical roundtrips under the ordinary service identity, private
ancestry at the first payload write, nested0700/0750/read-only/0000 directories,
empty directories, payload-first member ordering, identical/conflicting mode
duplicates, root records, legacy records, mode-application failures, and existing
exclusion/traversal behavior. Preserve bytes and existing file modes as well as
final directory modes. The real failed producer attempt must pass the after
probe; a synthetic ZIP-only unit test does not close A-S01.

This does not introduce an atomic restore guarantee, recover historical modes,
or prove old readers honor the added modes. Existing file-mode handling,
archive access policy and unrelated restore-hardening questions remain outside
this correction. Full package browser/archive/runtime acceptance remains open.

Reviewed SHA-256 values:

```text
artifact-observability-standard.md 0470093fe1aa4a143cab2d7f84051d9f1e4e910f7aabe866d3fe41a7b1b72245
archive_directory_contract_decision.md 1f5e8b952996b5987e4c1d0dfd7031c7b20a81b7e6d9921b7ec8ecc245a75171
```
