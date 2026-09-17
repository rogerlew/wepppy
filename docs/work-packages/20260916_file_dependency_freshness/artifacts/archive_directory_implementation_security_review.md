# A-S01 archive directory implementation security review

**PASS for the bounded implementation; A-S01 verified closed.** No unresolved
medium/high finding remains in this changed boundary. Reviewed
`wepppy/rq/project_rq_archive.py` after checkpoint `b8e9e3114` against the artifact
observability standard and `archive_directory_contract_decision.md`. Reviewer:
`freshness_security`; production and repository tests were not edited.

## Retained actual evidence

```text
wctl run-pytest docs/work-packages/20260916_file_dependency_freshness/artifacts/archive_attempt_permissions_security_probe_revision2.py docs/work-packages/20260916_file_dependency_freshness/artifacts/archive_directory_implementation_security_probe.py -v -s
```

`archive_directory_implementation_security_probe.log`: **9 passed in 9.19 s**.
The canonical operations use real filesystem access, ZIP files and project
lifecycle guards. Existing `ArchiveRuntime` supplies job/status/Redis transport
only. The service container ran as UID1000/GID993. Every project and alternate
path is disposable; no named project, live archive or external endpoint changed.

The unchanged original characterization is retained separately as
`archive_attempt_permissions_security_probe.py/.json/.log` (**1 failed**).
The revision2 script now passes the same actual failed Geneva `_Attempt`
roundtrip: both private ancestors remain0700, its readable0644 candidate remains
inside that barrier, status remains0600, ordinary directory0750 and private file
0600 survive, and every payload byte matches. The new ZIP contains explicit
ordinary directory metadata. The ZIP file's existing0644 policy is unchanged;
this correction does not introduce or claim a separate archive access policy.

The additional probe JSON records these real boundaries:

- A file-first ZIP with late parent/child records has owner-populatable ancestry
  established before the first payload `open('wb')`. Group/other bits never
  exceed the recorded directory bits. Final0000/0500/0750 parents, nested0400
  children and empty0711 directories are restored after population.
- Root-resolving `./` metadata cannot change the project's existing0750 mode.
  Identical mode records for `private/` and `./private/` succeed; conflicting
  records reject before any project deletion and preserve the prior marker.
- Legacy implicit parents and non-UNIX directory metadata retain actual umask
  behavior. Archive outputs and config transaction members remain excluded.
  The writer retains ordinary empty directories and does not traverse an
  existing directory symlink to an outside disposable fixture.
- Injected required directory chmod failure, both before payload and at final
  mode restoration, propagates through the existing failed-restore status;
  no success is published and the source archive remains available. Early
  failure creates no payload. Final failure retains the partial restored work.

## Scope and conformance

`_restore_directory_modes` validates explicit UNIX directory metadata before
destructive restoration, including mode0000 and conflicting resolved targets.
Recorded ancestors are established shallowest-first, retaining group/other
restrictions while adding only temporary owner access. Final application runs
deepest-first. Neither pass infers legacy modes or authorizes root chmod.
The writer uses existing traversal/exclusion decisions and adds ordinary
directory entries without following directory symlinks. Existing member path
validation, lifecycle lock, file ownership/mode behavior, archive naming,
selection and queue interfaces remain intact.

This scoped approval establishes the demonstrated producer privacy correction
under the actual local service identity. It does not certify arbitrary ACLs,
mixed ownership, mount behavior, malformed archive cases outside the existing
contract, or a new atomic/rollback guarantee for restore failures. Existing
file-mode exception handling and ZIP access are unchanged scope. Old archives
without usable directory records cannot recover historical modes; old readers
may ignore new records. Whole browse/HTTP/RQ/package acceptance remains separate.

Reviewed SHA-256:

```text
project_rq_archive.py 76a3dbfb305f3ac9a2d9c092dadb442754fc20231ccca4dd74b403221762a089
```
