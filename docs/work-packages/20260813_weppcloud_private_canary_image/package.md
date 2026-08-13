# WEPPcloud private-canary image compatibility

**Status**: Open (2026-08-13)
**Timezone**: UTC

## Overview

This package delivers the non-live WEPPpy half of the private WEPPcloud canary: a reproducible common-runtime image publication workflow and an additive local compatibility harness. It makes the minimum Caddy, WEPPcloud, and ephemeral Redis contract reviewable without changing or starting any production Compose deployment.

## Objectives

- Inventory the current production service, port, mount, secret, health-route, Caddy-route, and Docker-socket contracts.
- Publish the existing `docker/Dockerfile` image to private GHCR with a commit-derived tag, an immutable digest, and minimum `GITHUB_TOKEN` permissions.
- Exercise the same image through an additive Caddy + WEPPcloud + ephemeral Redis Compose smoke stack.
- Prove all tracked production Compose inputs remain byte-for-byte unchanged.

## Scope

### Included

- `.github/workflows/` image publication workflow with every Action pinned to a full commit SHA.
- Additive files under `docker/` for the minimum compatibility stack and focused tests.
- Package governance, compatibility evidence, validation results, and security review.

### Explicitly Out of Scope

- Any live Compose or Kubernetes deployment, restart, route, repository-setting, or credential change.
- Production/test-production secrets, PostgreSQL/NFS administration, or Kubernetes/Talos/SOPS/Cloudflare/Tailscale/pfSense access.
- RQ workers, Docker sockets, public routes, OAuth, SMTP, CAPTCHA, external-data credentials, or production Redis.
- Changes to existing production Compose defaults or deployment workflows.

## Stakeholders

- **Primary**: WEPPcloud operator and private-canary reviewers
- **Reviewers**: repository maintainers
- **Security Reviewer**: required before closure
- **Informed**: the paired `open-wepp-org` private-canary work package

## Success Criteria

- [ ] The inventory and minimum compatibility matrix are complete.
- [ ] The workflow uses only `contents: read` and `packages: write`, commit-derived tags, and full-SHA Action pins.
- [ ] A built image passes focused Compose rendering and runtime smoke checks, or an exact build failure is recorded.
- [x] The workflow reports the pushed immutable digest.
- [ ] Existing production Compose files are byte-for-byte unchanged.
- [ ] Lint/tests and a secret-sensitive diff review pass.
- [ ] A ready-for-review PR records the source SHA, image tag/digest, validation, and blockers.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: yes, in the active ExecPlan and tracker

## Dependencies

### Prerequisites

- Source baseline `2dedf916cb5ba430454dccc437ff0eb8fcb11daa` on `dev-01`.
- GitHub Actions and private GHCR publication using the repository-scoped `GITHUB_TOKEN`.

### Blocks

- The live, separately authorized private Kubernetes canary phase.

## Related Packages

- **Depends on**: `open-wepp-org/docs/work-packages/20260813-weppcloud-private-canary/`
- **Follow-up**: live private WEPPcloud canary and later RQ worker canary

## Timeline Estimate

- **Expected duration**: one focused implementation session plus CI completion
- **Complexity**: High
- **Risk level**: High

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: the package adds private image publication and repository-token permissions and defines secret/runtime boundaries.
- **Security review artifact**: `docs/work-packages/20260813_weppcloud_private_canary_image/artifacts/2026-08-13_security_review.md`

## References

- `docker/Dockerfile` - existing common runtime image build
- `docker/docker-compose.prod.yml` - protected base production contract
- `docker/docker-compose.prod.wepp1.yml` and `docker/docker-compose.prod.wepp3.yml` - protected host overrides
- `docker/docker-compose.prod.worker.yml` - protected worker/socket contract
- `/home/roger/src/open-wepp-org/docs/work-packages/20260813-weppcloud-private-canary/` - paired package (read-only during this dispatch)

## Deliverables

- Successful publication run: https://github.com/rogerlew/wepppy/actions/runs/31739217249
- Source image commit: `ed1b538df02a8db0d709257ea9dacc330c56b9d9`
- Published digest: `sha256:ee92666229df8fdffe4b06b1dff2cfd0e9e06823ada59915c8b492d8a468eb51`
- PR link pending creation after final validation.

## Follow-up Work

- Kubernetes manifests, live apply, production promotion, and worker compatibility remain separately governed and unauthorized here.
