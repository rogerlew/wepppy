# Bootstrap Git Maintenance

**Status**: Closed (2026-08-22)
**Timezone**: UTC

## Overview

Optimize newly enabled Bootstrap repositories before users clone them. The
background enable job will pack objects and write reachability bitmaps using
the RQ worker's existing `WEPPPY_NCPU` CPU budget.

## Scope

### Included

- Run fixed-argument `git gc` after the initial Bootstrap commit.
- Retain the existing run-scoped Git lock through maintenance.
- Use `WEPPPY_NCPU` as Git's pack-thread ceiling.
- Preserve normal Git prune grace periods and Compose compatibility.
- Test, review, publish, deploy to the private openWEPP canary, and benchmark
  the already initialized validation repository.

### Explicitly Out of Scope

- Periodic maintenance, maintenance after every automatic commit, or changing
  which run artifacts are tracked.
- Changes to Git authentication, authorization, hooks, routes, or production
  Compose configuration.

## Success Criteria

- [x] New Bootstrap enable jobs run Git maintenance under the existing lock.
- [x] Tests define the fixed command and configured CPU-budget contract; direct
  Git execution proves pack/bitmap creation.
- [x] Security and correctness reviews pass.
- [x] Canary runtime is deployed and the existing validation repository is
  maintained without changing its checked-out commit or working-tree content.
- [x] A post-maintenance clone is valid and its timing is recorded.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Decision provenance captured**: yes; Roger Lew directed use of the existing
  WEPPpy CPU-limit environment setting on 2026-08-22, implemented by Codex.

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: adds an RQ-worker Git subprocess that rewrites repository
  object storage on shared NFS.
- **Security review artifact**:
  `artifacts/20260822_security_review.md`

## Rollback

Revert the maintenance call and deploy the preceding image digest. Git object
packing is representation-only; refs and working-tree content remain unchanged.

## Deliverables

- WEPPpy PR 630 merged as `e94ead9d63a4ec6ca6507ef8a97082b9faba109a`.
- Immutable runtime image:
  `ghcr.io/rogerlew/wepppy@sha256:9cb4fed55f9d3f7b9873909ceddf9532958a4947f53e01eae9ea952d701aaecf`.
- openWEPP PR 128 deployed the image to default and batch RQ workers.
- Live maintenance completed in 28.0 seconds and preserved HEAD, tree, and
  working-status fingerprints. Clone time fell from 70.8 seconds to 4.65
  seconds and Git reported reuse of the single maintained pack.

## Follow-up Work

- Targeted pytest regressions remain authored but unexecuted because the active
  test workflow is pinned to offline `homelab` runners. Repair that runner-label
  dependency separately; live Git-boundary evidence closed this package.
