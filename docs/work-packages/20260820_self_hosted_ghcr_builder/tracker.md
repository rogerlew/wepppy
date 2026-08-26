# Tracker - Self-Hosted GHCR Builder

## Quick Status

**Timezone**: UTC

**Started**: 2026-08-21

**Current phase**: Closed

**Next milestone**: Canary deployment is tracked separately

**Security impact**: `high`

## Task Board

### Follow-up

- [ ] Upgrade pinned Actions before GitHub removes the Node 20 compatibility
  shim.
- [ ] Monitor the non-fatal BuildKit local-cache lock diagnostics and revise
  cache export only if they become job failures or prevent reuse.

### Done

- [x] Added `ghcr-builder` to online `runner-01` (2026-08-21).
- [x] Created user-owned persistent LFS and BuildKit cache roots (2026-08-21).
- [x] Seeded 1.2 GB / 632 LFS objects from the verified iMac checkout (2026-08-21).
- [x] Updated the common-image workflow and operator guidance (2026-08-21).
- [x] Parsed workflow YAML and exercised fresh-cache selection safely (2026-08-21).
- [x] Materialized 639 tracked LFS files at `0 B/s`; both LFS verification
  gates passed (2026-08-21).
- [x] Published the merged Climate finalizer source in trusted run
  [32454213155](https://github.com/rogerlew/wepppy/actions/runs/32454213155)
  (10m05s, 2026-08-21).
- [x] Repeated the identical-source build in run
  [32454946601](https://github.com/rogerlew/wepppy/actions/runs/32454946601)
  (4m39s); all expensive build layers reported `CACHED` and LFS verification
  passed again (2026-08-21).
- [x] Recorded the repeat digest and post-build cache/disk footprint
  (2026-08-21).
- [x] Completed independent review; removed `remote-ci` from `runner-01` and
  proved no pull-request selector can match its remaining labels (2026-08-21).
- [x] Hardened cache parent/path canonicalization, ownership, mode, directory,
  and symlink checks (2026-08-21).
- [x] Proved corrupt-LFS, unavailable-builder, and failed-build negative paths
  directly (2026-08-21).
- [x] Cleared the previously shared BuildKit cache and completed hardened run
  [32457043609](https://github.com/rogerlew/wepppy/actions/runs/32457043609)
  with cache promotion and digest reporting (2026-08-21).
- [x] Completed independent re-review with no unresolved medium/high findings
  (2026-08-21).

## Decisions

- **2026-08-21** - Dedicate `runner-01` to common-image publication so one
  machine owns one LFS and BuildKit cache. `runner-02` remains available for
  tests and recovery.
- **2026-08-21** - Keep caches under `/home/roger/.cache` because passwordless
  sudo is not currently available on `runner-01`; image publication does not
  require a privileged cache location.
- **2026-08-21** - Keep public pull-request workloads off `ghcr-builder`; only
  trusted `master` pushes and manual dispatches may publish.

## Risks

| Risk | Severity | Mitigation | Status |
| --- | --- | --- | --- |
| Untrusted PR code executes on persistent runner | High | No PR trigger; dedicated label; review workflow changes | Mitigated |
| Missing/corrupt cached LFS object enters image | High | Fetch current SHA, `git lfs fsck`, tracked-asset verifier | Mitigated |
| Concurrent builds corrupt local cache rotation | Medium | Workflow-level non-cancelling concurrency group | Mitigated |
| Cache fills 98 GB root filesystem | Medium | Record baseline and post-build use; monitor routinely | Mitigated; 73 GB free |
| Runner loss blocks publication | Medium | Revert to GitHub-hosted runner or prepare runner-02 | Accepted |
| Pinned Actions still target Node 20 | Low | GitHub currently forces Node 24; upgrade pins before compatibility removal | Open |
| BuildKit local exporter emits transient layer-lock diagnostics | Low | Both builds, cache promotion, and repeat reuse succeeded; monitor | Open |

## Validation

- [x] GitHub API readback shows `runner-01` online with `ghcr-builder`.
- [x] Source LFS store passed `git lfs fsck` before transfer.
- [x] Cache roots are owned by `roger` with mode `0700`.
- [x] Workflow YAML parses and `git diff --check` passes.
- [x] Fresh BuildKit cache selection emits an empty `cache-from` safely.
- [x] Runner-side LFS materialization and both verification gates pass.
- [x] Integration and repeat-build evidence recorded.
- [x] First build completed in 10m05s; same-source repeat completed in 4m39s.
- [x] Repeat imported the local cache manifest and reported `CACHED` for all
  expensive dependency, vendoring, static-build, and runtime-image steps.
- [x] Repeat published
  `sha256:fdc600987cc1d2e5a04a13b566a328b33555beb314b65c1d212c21e83e702960`.
- [x] Post-build cache is 2.6 GB BuildKit plus 1.2 GB LFS; root has 73 GB free.
- [x] API readback shows `runner-01` has no `remote-ci` or `homelab` label.
- [x] Parsed all `pull_request` and `pull_request_target` selectors; none can
  match `runner-01`'s remaining labels.
- [x] Disposable corrupted LFS object produced `corruptObject` and exit 1.
- [x] Missing-label run 32455822980 remained queued with zero steps and no
  fallback runner.
- [x] Forced-failure run 32455885190 skipped cache promotion; the prior cache
  index remained `13f98ae12e8fec7cd8a757bbedb056dd442337280b2791037ad6073282b99d49`.
- [x] Fresh-cache run 32456245898 exposed an overly strict first-promotion
  check; commit `151f6a821` corrected it before closure.
- [x] Final run 32457043609 passed all steps, retained cache mode `0700`, and
  published
  `sha256:02e57f4e1a47dc315d3f01fe6b1ce86e7bec6b7d05b6b8e04f4b5b39a7089593`.
