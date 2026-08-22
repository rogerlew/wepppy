# Bootstrap Git Maintenance

**Status**: Open (2026-08-22)
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

- [ ] New Bootstrap enable jobs run Git maintenance under the existing lock.
- [ ] Tests prove the fixed command uses the configured CPU budget.
- [ ] Security and correctness reviews pass.
- [ ] Canary runtime is deployed and the existing validation repository is
  maintained without changing its checked-out commit or working-tree content.
- [ ] A post-maintenance clone is valid and its timing is recorded.

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

