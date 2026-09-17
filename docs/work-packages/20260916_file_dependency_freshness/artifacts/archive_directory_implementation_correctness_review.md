# A-S01 archive directory correctness review

**Scoped PASS.** No blocking correctness finding remains in the directory-mode
implementation after checkpoint `b8e9e3114`. Reviewer: `freshness_correctness`.
Production and repository tests were read-only. This review independently
inspected the implementation and retained evidence; it did not rerun the probes.

`wepppy/rq/project_rq_archive.py` records traversed ordinary directories without
changing existing exclusions or following directory symlinks. Restore validates
explicit UNIX directory records, including permission0000, before destructive
cleanup. Identical resolved aliases agree; conflicting modes and file/directory
collisions reject before cleanup. Root-resolving records cannot chmod the project
root. Shallow-first staging adds temporary owner population access while retaining
the recorded group/other restrictions; deepest-first finalization restores the
recorded modes. Required directory chmod failures propagate through the existing
failed-restore boundary. Existing payload extraction, locking and cache cleanup
remain in the canonical workflow.

Evidence reviewed:

- `archive_directory_implementation_security_probe.log`: **9 passed**, actual
  filesystem/ZIP/lifecycle operations under UID1000/GID993. Only job/status/Redis
  transport uses the existing `ArchiveRuntime` seams. The actual failed Geneva
  attempt retains0700 ancestry,0600 status and exact payload bytes through the
  canonical archive/restore roundtrip. File-first ZIP ordering, restrictive and
  empty directories, root records, aliases, legacy metadata, exclusions, and
  early/final chmod failures are covered.
- The original failing permission roundtrip remains retained separately; it is
  not relabeled as passing. `archive_directory_tests_initial.log` has **30 passed,
  10 deselected**. The added repository tests exercise actual ZIP entries,
  pre-payload privacy and rejection before cleanup.
- `geneva_profile_archive_final_tests.log`: **135 passed** across its combined
  affected scope, not an archive-only test count.

The correction does not promise atomic restoration or rollback: a failure after
cleanup can retain a partial restored project and its source archive. Old ZIPs
without usable directory records cannot recover historical modes. Ownership,
ACLs, existing file-mode exception handling and ZIP access policy are unchanged.
Production-equivalent mounts/groups and the complete browse/HTTP/RQ workflow
remain separate runtime gates; this is not package completion.

Reviewed source SHA-256:

```text
project_rq_archive.py 76a3dbfb305f3ac9a2d9c092dadb442754fc20231ccca4dd74b403221762a089
```
