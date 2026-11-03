# Worktree cleanup, 2026-11-03 UTC

The operator requested classification and cleanup of all remaining changes after
WEPPpy release commit `94b3be9b8`. This cleanup changes documentation only; it
does not revise model behavior, scientific findings, release artifacts or defaults.

## Disposition

| Items | Action | Reason |
| --- | --- | --- |
| `wepppy/soils/ssurgo/ssurgo.md` | Commit clarification | Existing source confirms conductivity-based restriction detection, lower-boundary flags and terminal-depth padding; distinguish those from geological provenance and 200 mm boundary insertion. No parameterization changes. |
| `code-quality-report.json`, `code-quality-summary.md` | Restore HEAD | Generated observe-only snapshots from an earlier working tree, not current source changes or a new accepted baseline. |
| `wepppy/weppcloud/routes/usersum/generated/docs_index.json` | Restore HEAD | Generated index drift; no intended Usersum source edit. Included in this operator-requested whole-worktree cleanup. |
| 1,040 untracked rock/water artifacts | Retain privately; remove worktree copies | Investigation records and helpers outside the earlier finite reviewed Git selection. Preserve evidence without newly publishing private helpers or native-source material. |
| `mipa03_reference_discovery.bak` | Retain privately; remove worktree copy | Older draft; tracked `.md` corrects a typo and adds the port-boundary inventory. |

The rock/water package's historical review and retention records remain unchanged.
Existing large scientific archives were neither deleted nor rewritten. Private
references in historical documents remain private evidence references; the archive
below preserves the removed local paths for recovery.

## Recovery evidence

Private directory: `/wc1/holdouts/wepppy-worktree-cleanup-20261103-v1/`.
It contains `worktree-files.tar.gz`, `manifest.json`,
`archive-verification.json` and `cleanup-receipt.json`.

- Archive SHA256: `4686424de5dcfda8eb4bd9053c758d6e969c019358923825aeb31232aef3a984`.
- Manifest SHA256: `b835374f45068900be298621918c530fa247456bebc961e4faaa7350424872d9`.

The archive contains 1,045 regular files: all 1,041 untracked files and the four
modified tracked preimages. Every member's path, size, mode and SHA256 was checked
against the manifest by reading the completed archive. Live hashes and Git HEAD
were rechecked immediately before removing the finite listed copies and restoring
generated files. No blanket `git clean`, directory deletion or ignore rule was used.

Recover into a fresh directory first; member names are repository-relative:

```bash
mkdir /tmp/wepppy-cleanup-recovery
tar -xzf /wc1/holdouts/wepppy-worktree-cleanup-20261103-v1/worktree-files.tar.gz \
  -C /tmp/wepppy-cleanup-recovery
```

Compare recovered files with current source before selectively restoring anything
to the repository. This archive preserves historical state, not a current release
input set. The archive directory is private (0700); archive and manifest are 0600.

## Validation

SSURGO prose was checked against `wepppy/soils/ssurgo/ssurgo.py` detection and
serialization paths and the selected native lower-boundary consumers. Markdown
lint and spelling checks cover the documentation changes. Runtime tests are not
required for this documentation and worktree-cleanup change.
