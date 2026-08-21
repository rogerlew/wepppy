# Security Review - Self-Hosted GHCR Builder

## Metadata

- **Package**: `docs/work-packages/20260820_self_hosted_ghcr_builder/`
- **Reviewer**: Pending independent reviewer
- **Scope**: Persistent runner trust, package write token, caches, and cleanup
- **Commit context**: Pre-integration configuration

## Security Triage

- **Impact**: high
- **Reason**: A package-write workflow will execute on a persistent self-hosted
  runner attached to a public repository.
- **Trust boundary**: Only repository `master` pushes and explicit manual
  dispatches may select `ghcr-builder`; pull requests must never select it.

## Findings

| ID | Severity | Surface | Required action | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | High | Persistent public-repository runner | Confirm no PR trigger or reusable untrusted entry point can reach the job | Resolved; only `master` push and manual dispatch |
| SEC-02 | Medium | Cache paths and cleanup | Verify fixed paths, ownership, symlink resistance, and bounded deletion targets | Resolved in implementation; independent review pending |
| SEC-03 | Medium | Package credentials | Confirm job retains only `contents: read` and `packages: write` | Resolved; permissions unchanged |

## Current Controls

- All third-party Actions remain pinned to full commit SHAs.
- The job retains repository-scoped `GITHUB_TOKEN` permissions.
- Cache roots are fixed, user-owned, mode `0700`, and outside the checkout.
- Destructive cache rotation checks both exact expected paths before deletion.
- LFS objects are verified before the Docker build begins.

## Verdict

- **Gate status**: fail pending independent review and integration evidence
- **Release recommendation**: hold integration acceptance
