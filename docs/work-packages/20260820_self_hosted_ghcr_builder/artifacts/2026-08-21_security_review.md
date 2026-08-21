# Security Review - Self-Hosted GHCR Builder

## Metadata

- **Package**: `docs/work-packages/20260820_self_hosted_ghcr_builder/`
- **Reviewer**: Independent Codex review (Goodall)
- **Scope**: Persistent runner trust, package write token, caches, and cleanup
- **Commit context**: Integration evidence through source
  `78cb5cfeca5db7528cb34e638ceb5c203cdc5a00`

## Security Triage

- **Impact**: high
- **Reason**: A package-write workflow will execute on a persistent self-hosted
  runner attached to a public repository.
- **Trust boundary**: Only repository `master` pushes and explicit manual
  dispatches may select `ghcr-builder`; pull requests must never select it.

## Findings

| ID | Severity | Surface | Required action | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | High | Persistent public-repository runner | Initial review found `remote-ci` allowed PR jobs onto `runner-01`; remove general eligibility and recheck selectors | Resolved; label removed, no PR/PR-target selector matches remaining labels |
| SEC-02 | Medium | Cache paths and cleanup | Verify canonical paths, trusted parent, ownership, mode, symlink resistance, and bounded deletion targets | Resolved; hardened checks and final live run passed |
| SEC-03 | Medium | Package credentials | Confirm job retains only `contents: read` and `packages: write` | Resolved; permissions unchanged |

## Current Controls

- All third-party Actions remain pinned to full commit SHAs.
- The job retains repository-scoped `GITHUB_TOKEN` permissions.
- Cache roots are fixed, user-owned, mode `0700`, and outside the checkout.
- Destructive cache rotation checks both exact expected paths before deletion.
- LFS objects are verified before the Docker build begins.

## Verdict

- **Gate status**: pass
- **Release recommendation**: close package; no unresolved medium/high findings

## Integration Evidence

- Both trusted manual-dispatch runs used only the dedicated `ghcr-builder`
  runner and repository-scoped `GITHUB_TOKEN`.
- The fixed cache-path ownership and symlink checks passed before both builds;
  cache promotion completed after each successful image push.
- No credential material appears in the reviewed logs.
- Repeat-build cache reuse succeeded with 73 GB free after completion.

## Independent Review and Remediation

- The first independent pass correctly rejected the claim that `runner-01`
  was dedicated: it still carried `remote-ci`, which several pull-request jobs
  selected. That label was removed. API readback now shows only `self-hosted`,
  `Linux`, `X64`, `wepppy`, and `ghcr-builder`.
- An independent parse of all `pull_request` and `pull_request_target` jobs
  found no selector whose required labels are a subset of the remaining
  runner labels.
- Cache preparation/promotion now verifies canonical `/home/roger/.cache`,
  owner/mode `roger:0700`, exact leaf paths, directory type, leaf ownership,
  and absence of leaf symlinks before deletion or promotion.
- The BuildKit cache that existed while `remote-ci` was present was deleted.
  The LFS store was retained because every object is content-addressed and both
  `git lfs fsck` and the repository materialization verifier gate each build.
- Final run
  [32457043609](https://github.com/rogerlew/wepppy/actions/runs/32457043609)
  passed all steps with cache mode `0700`, 73 GB free, masked credentials, and
  only `contents: read`, `metadata: read`, and `packages: write` permissions.

## Accepted Low Follow-ups

- Upgrade pinned Actions before GitHub removes its Node 20 compatibility shim.
- Continue routine cache-capacity and transient local-export lock monitoring.
- Treat the SHA-derived tag as a convenient commit tag, not an immutable
  identifier; only the digest-qualified image reference is immutable.
