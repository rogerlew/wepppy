# Correctness Review - Self-Hosted GHCR Builder

## Metadata

- **Package**: `docs/work-packages/20260820_self_hosted_ghcr_builder/`
- **Reviewer**: Independent Codex review (Goodall)
- **Scope**: Common-image checkout, LFS materialization, cache, build, and push
- **Commit context**: Integration evidence through source
  `78cb5cfeca5db7528cb34e638ceb5c203cdc5a00`

## Required Outcomes

- Fresh cache: fetch all required objects, verify, build, and publish.
- Populated cache: fetch only missing objects and materialize the same tree.
- Corrupt cache object: fail before image build.
- Missing builder: queue visibly without falling back to an unintended runner.
- Failed image build: do not promote the incomplete next BuildKit cache.
- Successful build: report immutable source tag and digest as before.

## Findings

| ID | Severity | Description | Required action | Status |
| --- | --- | --- | --- | --- |
| COR-01 | High | Integration publication and repeat-build cache evidence were deferred | Trusted runs 32454213155 and 32454946601 passed; repeat LFS verification passed and all expensive image layers reported `CACHED` | Resolved; independently reviewed |
| COR-02 | Medium | Corrupt-LFS, failed-build, and unavailable-builder states lacked direct evidence | Executed disposable corruption test and runs 32455822980/32455885190 | Resolved |
| COR-03 | Medium | Hardened promotion initially rejected a valid absent-first-cache state | Run 32456245898 exposed the failure; optional-old-cache logic fixed in `151f6a821`; run 32457043609 passed | Resolved |

## Verdict

- **Gate status**: pass
- **Release recommendation**: close package; no unresolved medium/high findings

## Integration Evidence

- First build: [run 32454213155](https://github.com/rogerlew/wepppy/actions/runs/32454213155),
  10m05s.
- Same-source repeat: [run 32454946601](https://github.com/rogerlew/wepppy/actions/runs/32454946601),
  4m39s.
- Both runs materialized and verified all 639 tracked LFS files.
- The repeat imported `/home/roger/.cache/wepppy-buildx` and reported `CACHED`
  for the package install, dependency vendoring, static compilation, repository
  copy/verification, and final runtime layer.
- The repeat published digest
  `sha256:fdc600987cc1d2e5a04a13b566a328b33555beb314b65c1d212c21e83e702960`.

## Negative and Remediation Evidence

- A disposable hard-linked copy of the LFS object store had one tracked object
  replaced with invalid bytes. `git lfs fsck` exited 1 and reported
  `corruptObject` before any Docker build.
- Removing `ghcr-builder` made run
  [32455822980](https://github.com/rogerlew/wepppy/actions/runs/32455822980)
  remain queued with zero steps. It was cancelled and the label restored; no
  fallback runner executed it.
- Intentional build-failure run
  [32455885190](https://github.com/rogerlew/wepppy/actions/runs/32455885190)
  failed in the Docker build and skipped promotion/reporting. The old cache
  index SHA-256 remained
  `13f98ae12e8fec7cd8a757bbedb056dd442337280b2791037ad6073282b99d49`.
  The temporary failure was exactly reverted in `c5a0a7c46`.
- Clean-cache run
  [32456245898](https://github.com/rogerlew/wepppy/actions/runs/32456245898)
  exposed a valid absent-old-cache promotion state. The fix in `151f6a821` was
  validated by final run
  [32457043609](https://github.com/rogerlew/wepppy/actions/runs/32457043609),
  which passed every step and reported the immutable digest.
