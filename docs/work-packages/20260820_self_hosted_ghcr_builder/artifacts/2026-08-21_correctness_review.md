# Correctness Review - Self-Hosted GHCR Builder

## Metadata

- **Package**: `docs/work-packages/20260820_self_hosted_ghcr_builder/`
- **Reviewer**: Pending independent reviewer
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
| COR-01 | High | Integration publication and repeat-build cache evidence were deferred | Trusted runs 32454213155 and 32454946601 passed; repeat LFS verification passed and all expensive image layers reported `CACHED` | Resolved; independent review pending |

## Verdict

- **Gate status**: fail pending independent review
- **Release recommendation**: integration evidence is complete; hold package
  closure until an independent reviewer confirms the evidence and remaining
  states

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
