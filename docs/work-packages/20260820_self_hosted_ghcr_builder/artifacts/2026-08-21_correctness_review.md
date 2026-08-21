# Correctness Review - Self-Hosted GHCR Builder

## Metadata

- **Package**: `docs/work-packages/20260820_self_hosted_ghcr_builder/`
- **Reviewer**: Pending independent reviewer
- **Scope**: Common-image checkout, LFS materialization, cache, build, and push
- **Commit context**: Pre-integration configuration

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
| COR-01 | High | Integration publication and repeat-build cache evidence are deferred | Execute after Climate finalizer and compare logs/digest reporting | Open |

## Verdict

- **Gate status**: fail
- **Release recommendation**: hold integration acceptance
