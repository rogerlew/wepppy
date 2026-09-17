# Archive directory preservation: independent QA

**Scoped PASS.** The implementation after contract checkpoint `b8e9e3114`
closes the demonstrated retained-attempt directory-mode loss. No blocking
maintainability or test-quality finding remains in this change. Reviewer:
`freshness_qa`, 2026-09-17. Production and tests were read-only.

## Implementation and meaningful coverage

`wepppy/rq/project_rq_archive.py` adds one focused metadata validator and two
ordered restore passes. The writer records traversed ordinary directories,
including empty ones. Validation precedes destructive cleanup; recorded
ancestry is established shallowest-first before any payload write, with only
temporary owner population access. Final modes are applied deepest-first.
The implementation reuses existing path validation, traversal exclusions and
lifecycle guards. It introduces no parallel archive store or queue interface.

The added repository tests assert actual ZIP entries and restored bytes/modes,
including empty folders, a file-first archive, permission0000, unchanged project
root permissions and conflicting metadata rejected before cleanup. The
first-payload-write assertion is valuable: a final-mode-only assertion would
miss a temporary privacy regression. Required chmod errors propagate through
the existing failed-restore path instead of becoming successful partial restores.

Reviewed evidence:

- `archive_directory_tests_initial.log`: **30 passed, 10 deselected**.
- `archive_directory_implementation_security_probe.log`: **9 passed**. Real
  filesystem/ZIP operations and lifecycle guards under UID1000/GID993; the
  existing `ArchiveRuntime` supplies job/status/Redis transport. The actual
  failed Geneva producer attempt retains private0700 ancestry, candidate/status
  bytes and ordinary0750 directory/file0600 modes after canonical restore.
- The same independent probes cover identical versus conflicting resolved
  aliases, root entries, legacy implicit/non-UNIX modes, exclusions, directory
  symlink nontraversal, restrictive nested/empty directories, and failures both
  before payload creation and during final chmod. Failure evidence and the
  original archive remain available.
- `geneva_profile_archive_final_tests.log`: **135 passed** across the combined
  affected scope; this is not an archive-only count.

The original failed permission roundtrip remains retained in
`archive_attempt_permissions_security_probe.py/.json/.log`. Its failure is not
relabeled as a pass. The current source SHA-256 still matches the independent
security review:

```text
76a3dbfb305f3ac9a2d9c092dadb442754fc20231ccca4dd74b403221762a089
```

## Residual debt and acceptance limits

The new helper's untyped member tuples match adjacent archive helpers; naming
and ordering make the small control flow understandable. A future local cleanup
may type that tuple contract without restructuring restoration. More useful
regression hardening is to promote the retained chmod-failure and legacy
non-UNIX metadata cases into the repository suite when this module next changes;
they currently run as independent retained probes. Neither follow-up blocks this
bounded acceptance.

Existing file-mode exception handling, archive-file access, ownership, ACLs and
restore rollback semantics are unchanged. Old ZIPs without usable directory
records cannot recover historical modes. The local service-identity proof does
not establish every production mount/group configuration, remote browser
download or full RQ workflow. Those package runtime gates remain separate. This
review accepts the explicit directory-metadata contract in the artifact
observability standard; it does not mark the freshness package complete.
