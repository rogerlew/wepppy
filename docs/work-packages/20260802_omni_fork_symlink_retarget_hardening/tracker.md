# Tracker - Omni Fork Symlink Retarget Hardening

**Started**: 2026-08-02 18:28 UTC
**Phase**: Implementation validation
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
- [ ] Commit the amendment as a standalone ancestor and complete adversarial
  regression coverage.
- [ ] Run targeted/full validation and final reviews.
- [ ] Close locally without deployment.

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

## Validation

- [ ] `wctl run-pytest tests/rq/test_project_rq_fork.py --maxfail=1`
- [ ] Targeted Omni clone tests.
- [ ] `wctl run-pytest tests --maxfail=1`
- [ ] Changed broad-exception enforcement, docs lint, and `git diff --check`.
- [ ] Generated one- and two-generation destination inspection.

## Incident Timeline and Risks

- **2026-02-08 UTC** – Scenarios created in `mdobre-facile-deviousness` with
  absolute shared-input links.
- **2026-05/06 UTC** – Later fork generations preserved old and newly created
  absolute links.
- **2026-08-02 16:51 and 17:09 UTC** – Two archives failed on the inherited
  dangling `prescribed_fire/climate` link.
- **2026-08-02 18:28 UTC** – Operator selected rsync-preserving fork hardening.

Open risks are parent-swap/link escape, partial normalization, legacy `.nodir`
compatibility, and wall-time regression. Codex owns automated containment and
rollback evidence; the operator owns later Forest/production latency evidence.
No temporary callus is registered.

Final review discovered that root-only rsync exclusions can leave copied
contrast-run symlinks dangling. The contract now makes their transactional
removal explicit in skip/undisturbify mode; this amendment requires checkpoint
confirmation before the implementation commit.
