# Tracker - Omni Fork Symlink Retarget Hardening

**Started**: 2026-08-02 18:28 UTC
**Phase**: Reopened; NFS compatibility remediation
**Security**: high; dedicated review required

## Tasks

- [x] Capture production lineage and freeze rsync-preserving scope.
- [x] Scaffold package, ExecPlan, decision, and security gate.
- [x] Receive two checkpoint reviews; initial checkpoint rejected.
- [x] Expand exact roles, producer scope, no-follow transaction, and lifecycle
  evidence in response to findings.
- [x] Dual-review and disposition the standalone checkpoint.
- [x] Commit the standalone checkpoint ancestor (`9d437942f2c78ea54cb66e4bfd2cb454670d7995`).
- [x] Add initial regressions and implement hardening.
- [x] Ratify the skip/undisturbify contrast-run amendment discovered in final
  review with independent contract and security approval.
- [x] Commit amendment ancestors and complete adversarial regression coverage.
- [x] Ratify the exact `build_report.ndjson` metadata exception with independent
  contract and security approval and complete its regression matrix.
- [x] Ratify capture-first private-quarantine publication/rollback and its
  explicit threat boundary with independent approval.
- [x] Run targeted/full validation and final reviews.
- [x] Close locally without deployment.
- [x] Capture production failure
  `c4a6e8cc-a2cf-48bc-9d77-e97e7727a53b` (`EINVAL` from NFS renameat2).
- [x] Ratify an NFS-compatible capture/restore transaction with independent
  contract and security approval.
- [x] Implement and validate the transaction on the `/wc1` NFSv4.2 mount
  (`3 passed`; no temporary workspace residue).
- [ ] Repeat final correctness, QA, and security gates.
- [x] Capture access-log sidecar fork failure
  `8dda9f7a-310f-4a16-8bae-501a2d0106d6` and amend the collection contract.
- [x] Add an exact dot-sidecar regression.
- [ ] Complete dual amendment review, standalone checkpoint, full validation,
  and final disposition.

## Decisions

- **2026-08-02 18:28 UTC** – Keep `rsync -a`; a new copy engine requires
  separate benchmark evidence.
- **2026-08-02 18:28 UTC** – Normalize recognized links by semantic role, not
  old target prefix, so missing grandparent links are repairable.
- **2026-08-02 18:28 UTC** – Preserve unrelated symlinks and fail explicitly
  rather than silently skipping data.
- **2026-08-02 19:50 UTC** – In skip/undisturbify mode, remove copied contrast
  `wepp/runs` symlinks transactionally because their destination root targets
  are intentionally excluded; retain regular materialized files.
- **2026-08-02 20:45 UTC** – Retain only the canonical collection metadata file
  `build_report.ndjson`; reject all other non-directory collection entries.
- **2026-08-06 07:03 UTC** – Skip dot-prefixed collection entries during link
  normalization regardless of type; preserve historical copy/archive behavior
  and treat access-log privacy as a separate surface.

## Validation

- [x] Historical pre-remediation fork suite: `62 passed`.
- [x] Current remediation fork suite: `63 passed`.
- [x] Current focused suite: `161 passed, 1 skipped` (explicit NFS case runs
  separately).
- [x] Actual `/wc1` NFSv4.2 integration: `3 passed` in `8.28s`, including
  regular-file and directory pre-capture swaps.
- [x] Live rq-engine fork/archive smoke: fork completed in `14.8065s` with 63
  valid target-relative Omni links; 282 MB archive completed in `103.636748s`.
- [x] Historical pre-remediation full suite: `5783 passed, 58 skipped`.
- [x] Current post-remediation full suite: `5844 passed, 61 skipped`.
- [x] Access-log amendment focused suite: `65 passed`.
- [x] Changed broad-exception enforcement, docs lint, and `git diff --check`.
- [x] Missing-ancestor, relative-target, and multi-mode destination evidence in
  focused regression fixtures.

## Incident Timeline and Risks

- **2026-02-08 UTC** – Scenarios created in `mdobre-facile-deviousness` with
  absolute shared-input links.
- **2026-05/06 UTC** – Later fork generations preserved old and newly created
  absolute links.
- **2026-08-02 16:51 and 17:09 UTC** – Two archives failed on the inherited
  dangling `prescribed_fire/climate` link.
- **2026-08-02 18:28 UTC** – Operator selected rsync-preserving fork hardening.
- **2026-08-06 06:03 UTC** – Fork job
  `8dda9f7a-310f-4a16-8bae-501a2d0106d6` failed on regular legacy sidecar
  `scenarios/.mulch_15_sbs_map` after copying destination
  `storied-centralism`.
- **2026-08-06 PDT** – Operator directed the normalizer to skip these rare
  legacy sidecars.

Open risks are parent-swap/link escape, partial normalization, legacy `.nodir`
compatibility, and wall-time regression. Codex owns automated containment and
rollback evidence; the operator owns later Forest/production latency evidence.
No temporary callus is registered.

Access-log amendment baseline: one recurrence. Health is zero recurrence for
30 days after deployment. The guardrail is continued rejection of ordinary
unexpected collection entries.

### Reopen Note — 2026-08-02

Production proved that Linux syscall availability is not equivalent to backing
filesystem support. Ext4 tests accepted `RENAME_NOREPLACE`; the production
NFSv4.2 export did not. The remediation must test the exact symlink capture,
exclusive restore, and cleanup operations on NFS before closure.

Final review discovered that root-only rsync exclusions can leave copied
contrast-run symlinks dangling. The contract now makes their transactional
removal explicit in skip/undisturbify mode; this amendment requires checkpoint
confirmation before the implementation commit.
