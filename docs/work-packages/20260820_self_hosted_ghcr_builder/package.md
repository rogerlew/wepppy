# Self-Hosted GHCR Builder

**Status**: Closed (2026-08-21)
**Timezone**: UTC

## Overview

Move the trusted WEPPcloud common-image publication job from disposable
GitHub-hosted compute to `runner-01`. Reuse locally seeded Git LFS objects and
Docker BuildKit layers so repeated image builds consume only missing LFS
objects and changed build layers.

## Objectives

- Route common-image publication exclusively to the `ghcr-builder` runner.
- Preserve the existing trusted `master` push and manual-dispatch triggers.
- Materialize and verify every tracked LFS asset from a persistent local store.
- Retain BuildKit cache only after a successful image build.
- Keep GHCR authentication limited to the repository `GITHUB_TOKEN`.

## Scope

### Included

- `runner-01` label and user-owned persistent cache directories.
- `.github/workflows/publish-weppcloud-image.yml` runner and cache changes.
- Workflow operator guidance and governed review evidence.

### Explicitly Out of Scope

- Allowing pull-request jobs on the persistent builder.
- Moving auxiliary-image workflows or general CI to this runner.
- Sharing caches between `runner-01` and `runner-02`.

## Success Criteria

- [x] `runner-01` is online with the `ghcr-builder` label.
- [x] Its LFS cache is seeded from a verified local checkout without GitHub LFS
  transfer.
- [x] Static workflow and runner-side cache-path validation pass.
- [x] A trusted integration publication succeeds after the Climate finalizer.
- [x] A second no-source-change build demonstrates LFS and BuildKit reuse.
- [x] No unresolved medium/high correctness or security findings remain.

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The change routes a public repository's package-write
  workflow to a persistent self-hosted machine and retains source/build caches.
- **Security review artifact**:
  [`artifacts/2026-08-21_security_review.md`](artifacts/2026-08-21_security_review.md)

## Operational Facts

- Runner: `runner-01`; required labels `self-hosted`, `Linux`, `X64`,
  `ghcr-builder`.
- LFS store: `/home/roger/.cache/wepppy-lfs` (`0700`).
- BuildKit cache: `/home/roger/.cache/wepppy-buildx` (`0700`).
- Initial LFS seed: 1.2 GB / 632 object files copied from the iMac after
  `git lfs fsck` passed.
- Runner workspace verification: 639 tracked LFS files materialized with
  `0 B/s` from the seeded store; `git lfs fsck` and the repository verifier
  passed.
- Runner root filesystem: 98 GB with 78 GB free before the first build.
- Integration run
  [32454213155](https://github.com/rogerlew/wepppy/actions/runs/32454213155)
  published source `78cb5cfeca5db7528cb34e638ceb5c203cdc5a00` in 10m05s.
- Same-source repeat run
  [32454946601](https://github.com/rogerlew/wepppy/actions/runs/32454946601)
  completed in 4m39s. All expensive dependency, vendoring, static-build, and
  runtime-image steps reported `CACHED`; 639 tracked LFS files passed both
  verification gates from the persistent 1.2 GB object store.
- Current commit tag:
  `ghcr.io/rogerlew/wepppy:sha-78cb5cfeca5db7528cb34e638ceb5c203cdc5a00`;
  repeat-build digest:
  `sha256:fdc600987cc1d2e5a04a13b566a328b33555beb314b65c1d212c21e83e702960`.
- Post-build cache footprint: 2.6 GB BuildKit plus 1.2 GB LFS; runner root
  filesystem has 73 GB free (22% used).
- Independent review initially found that `runner-01` could also accept
  pull-request jobs through its `remote-ci` label. The label was removed, all
  PR selectors were checked against the remaining labels, the potentially
  exposed BuildKit cache was discarded, and a clean trusted image was built.
- Final hardened run
  [32457043609](https://github.com/rogerlew/wepppy/actions/runs/32457043609)
  passed end to end at source `151f6a8216068b61dcc769c5b5bdae3f5fcc127e`.
  It published immutable digest
  `sha256:02e57f4e1a47dc315d3f01fe6b1ce86e7bec6b7d05b6b8e04f4b5b39a7089593`.
- Direct negative tests proved corrupt LFS rejection, no runner fallback when
  the dedicated label is absent, and no cache promotion after a failed build.
- Rollback: restore `runs-on: ubuntu-24.04` and remove the local cache options;
  removing the GitHub runner label is independently reversible.

## Related Packages

- [`20260813_weppcloud_private_canary_image`](../20260813_weppcloud_private_canary_image/package.md)
- [`20260820_climate_finalize_lock`](../20260820_climate_finalize_lock/package.md)

## References

- `.github/workflows/publish-weppcloud-image.yml`
- `.github/workflows/AGENTS.md`
- `tools/verify_lfs_materialized.py`

## Closure Summary

The dedicated builder, persistent verified LFS store, guarded BuildKit cache,
trusted trigger boundary, negative-path evidence, and final publication are
complete. Independent correctness and security review found no unresolved
medium/high findings. Node 20 Action compatibility and routine cache-capacity
monitoring remain low-priority operational follow-ups.
