# Self-Hosted GHCR Builder

**Status**: Open (2026-08-21)
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

- Running the first integration image build before the Climate finalizer lands.
- Allowing pull-request jobs on the persistent builder.
- Moving auxiliary-image workflows or general CI to this runner.
- Sharing caches between `runner-01` and `runner-02`.

## Success Criteria

- [x] `runner-01` is online with the `ghcr-builder` label.
- [x] Its LFS cache is seeded from a verified local checkout without GitHub LFS
  transfer.
- [x] Static workflow and runner-side cache-path validation pass.
- [ ] A trusted integration publication succeeds after the Climate finalizer.
- [ ] A second no-source-change build demonstrates LFS and BuildKit reuse.
- [ ] No unresolved medium/high correctness or security findings remain.

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
- Rollback: restore `runs-on: ubuntu-24.04` and remove the local cache options;
  removing the GitHub runner label is independently reversible.

## Related Packages

- [`20260813_weppcloud_private_canary_image`](../20260813_weppcloud_private_canary_image/package.md)
- [`20260820_climate_finalize_lock`](../20260820_climate_finalize_lock/package.md)

## References

- `.github/workflows/publish-weppcloud-image.yml`
- `.github/workflows/AGENTS.md`
- `tools/verify_lfs_materialized.py`
