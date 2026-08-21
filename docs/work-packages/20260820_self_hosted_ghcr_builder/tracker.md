# Tracker - Self-Hosted GHCR Builder

## Quick Status

**Timezone**: UTC

**Started**: 2026-08-21

**Current phase**: Configuration complete / integration deferred

**Next milestone**: Integration publication after Climate finalizer completion

**Security impact**: `high`

## Task Board

### Ready / Backlog

- [ ] Complete independent correctness and security reviews.
- [ ] Run the deferred trusted integration publication.
- [ ] Repeat the build and record cache-hit/LFS-transfer evidence.

### Blocked

- [ ] Integration publication waits for the Climate finalizer implementation.

### Done

- [x] Added `ghcr-builder` to online `runner-01` (2026-08-21).
- [x] Created user-owned persistent LFS and BuildKit cache roots (2026-08-21).
- [x] Seeded 1.2 GB / 632 LFS objects from the verified iMac checkout (2026-08-21).
- [x] Updated the common-image workflow and operator guidance (2026-08-21).
- [x] Parsed workflow YAML and exercised fresh-cache selection safely (2026-08-21).
- [x] Materialized 639 tracked LFS files at `0 B/s`; both LFS verification
  gates passed (2026-08-21).

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
| Cache fills 98 GB root filesystem | Medium | Record baseline; inspect disk after integration build | Open |
| Runner loss blocks publication | Medium | Revert to GitHub-hosted runner or prepare runner-02 | Accepted |

## Validation

- [x] GitHub API readback shows `runner-01` online with `ghcr-builder`.
- [x] Source LFS store passed `git lfs fsck` before transfer.
- [x] Cache roots are owned by `roger` with mode `0700`.
- [x] Workflow YAML parses and `git diff --check` passes.
- [x] Fresh BuildKit cache selection emits an empty `cache-from` safely.
- [x] Runner-side LFS materialization and both verification gates pass.
- [ ] Integration and repeat-build evidence recorded.
