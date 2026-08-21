# WEPPcloudR Execution Backend Refactor

**Status**: Open (2026-08-21)
**Timezone**: UTC

## Overview

Implement the repository-side execution boundary in
`docs/schemas/weppcloudr-render-execution-contract.md` while preserving the
existing Docker Compose behavior. Compose deployments must continue rendering
DEVAL In The Details through Docker exec with their current mounts. The
Kubernetes path will gain testable orchestration and renderer interfaces, but
building, publishing, or deploying Kubernetes containers and manifests belongs
to a separate package.

## Objectives

- Refactor `wepppy.rq.weppcloudr_rq` behind explicit `docker-exec` and
  `kubernetes-job` backend interfaces without changing the public report/UI
  contract.
- Preserve the exact Compose service mounts and the live Docker-exec render path.
- Implement and test the versioned render request, run-WD boundary, durable
  receipt, reconciliation, cancellation, failure, logging, locking, and fencing
  contracts that can be proven without deploying Kubernetes.
- Add the one-shot WEPPcloudR renderer entrypoint and repository-side control-
  plane/client surfaces needed by the future Kubernetes deployment.
- Restart the authorized forest development stack and prove DEVAL rendering on
  `branching-hubbub/disturbed9002_wbt` still completes through Docker exec.

## Scope

### Included

- Backend selection and shared orchestration in `wepppy/rq/weppcloudr_rq.py`
  and its stub/API surfaces.
- Passing canonical `run_root` alongside `active_root` from the DEVAL enqueue
  boundary while preserving legacy queued Compose arguments.
- Docker-exec adapter behavior, timeout/error handling, bounded protected logs,
  artifact validation, cache semantics, and regression tests.
- Kubernetes Job specification, state-machine, control-plane protocol, and
  client logic testable with deterministic fakes or a disposable local test
  API. Implementation does not equal deployment.
- WEPPcloudR source changes for the strict request-v1 parser and one-shot
  renderer entrypoint. No image publication is included.
- Queue/dependency catalog and configuration documentation updates required by
  repository changes.
- Focused, broad, correctness, QA, and security review gates.
- Authorized forest integration: update/restart only the development Compose
  stack serving `wc.bearhive.duckdns.org`, then request DEVAL In The Details for
  the designated run and capture job, log, artifact, and mount evidence.

### Explicitly Out of Scope

- Building, publishing, signing, or promoting a Kubernetes `weppcloudr` image.
- Authoring or applying production Kubernetes/GitOps manifests, PVs/PVCs,
  NetworkPolicies, RBAC, admission policies, Services, Deployments, or Jobs.
- Any live Kubernetes cluster deployment or end-to-end Kubernetes render.
- Restarting `forest1`, `wepp1`, `wepp2`, `wepp3`, production, or any service
  outside the forest development stack.
- Changing any current Compose mount, volume, container name, network, or
  Docker-socket contract.
- Replacing Docker exec for Compose, merging WEPPpy and WEPPcloudR images, or
  removing the `weppcloudr` Compose service.
- Modifying the designated run except for the normal DEVAL cache/log/artifact
  writes caused by an authorized report request.
- General RQ, Kubernetes batch-platform, NFS, or run-layout redesign.

## Implementation Fidelity and Evidence

- **Fidelity target**: `faithful extraction`
- **Authoritative source paths**:
  `wepppy/rq/weppcloudr_rq.py`,
  `wepppy/weppcloud/routes/weppcloudr.py`,
  `weppcloudR/plumber.R`, and
  `docs/schemas/weppcloudr-render-execution-contract.md`
- **Cutover proof required**: Compose remains wired to `docker-exec`; a real
  forest request creates/refreshes the expected DEVAL HTML through the running
  `weppcloudr` container. Kubernetes code is reported only as implemented and
  testable, never deployed or wired.
- **Acceptance evidence type**: `both`; generated-output evidence is mandatory
  for Compose, while Kubernetes uses repository integration/state-machine
  evidence until the separate deployment package.

## Stakeholders

- **Primary**: WEPPcloud operators and users of DEVAL In The Details
- **Reviewers**: RQ, WEPPcloud, Docker Compose, and QA maintainers
- **Security Reviewer**: independent security reviewer required before closure
- **Informed**: maintainers of the separate Kubernetes build/deployment package

## Success Criteria

- [ ] Backend selection is explicit and fails closed; Kubernetes never falls
  back to Docker and Compose defaults remain compatible.
- [ ] Compose files have byte-for-byte unchanged `weppcloudr` and worker mount
  definitions relative to package start.
- [ ] Existing and new Compose-focused unit/integration tests pass.
- [ ] Kubernetes orchestration behavior required by the canonical contract is
  implemented and deterministically tested without claiming cluster deployment.
- [ ] RQ graph/catalog, stubs, configuration, operator, and module docs match
  the implemented interfaces.
- [ ] Independent correctness, QA, and security reviews have no unresolved
  medium/high findings.
- [ ] After an authorized forest development-stack restart, the designated
  DEVAL report completes through Docker exec, produces a valid HTML artifact,
  and retains the established mounts.
- [ ] No Kubernetes image build, publication, manifest apply, or deployment is
  performed by this package.

## Parameterization ADR Gate

- **Parameterization change present**: `no`
- **ADR required**: `no`
- **ADR link(s)**: N/A
- **Decision provenance captured**: `yes`; operator and Codex discussion on
  2026-08-21, with rationale in the canonical contract and this package.

## Dependencies

### Prerequisites

- `docs/schemas/weppcloudr-render-execution-contract.md` at or after commit
  `946f14518`.
- Existing forest development Compose stack and designated run remain
  available.
- Access to the WEPPcloudR source used by `docker/weppcloudR/Dockerfile`.

### Blocks

- Separate Kubernetes image-build, registry-publish, manifest, and deployment
  work.
- Any claim that `kubernetes-job` is deployable in the target cluster.

## Related Packages

- **Depends on**: [WEPPcloudR render contract review](../../dev-notes/weppcloudr-render-execution-contract-review-2026-08-21.md)
- **Related**: [Direct OpenFileGDB cutover](../20260821_openfilegdb_cutover/package.md)
- **Follow-up**: separately governed Kubernetes image build and deployment
  package, to be named and authorized by its owner.

## Timeline Estimate

- **Expected duration**: 3-6 focused sessions plus independent review
- **Complexity**: High
- **Risk level**: High

## Security Impact and Review Gate

- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: the package changes RQ execution, subprocess and file
  boundaries, internal workload-control protocol, cancellation, logging, and
  future Kubernetes authority surfaces.
- **Security review artifact**:
  `docs/work-packages/20260821_weppcloudr_execution_backend_refactor/artifacts/2026-08-21_security_review.md`

## Hardening and Callus Softening

This is an architectural refactor rather than incident remediation. The
hardening lifecycle standard does not add an observation-window gate, but the
package must avoid speculative compatibility wrappers and retain only the
explicit legacy queued-job shim authorized by the contract.

## Forest Authorization Boundary

The operator explicitly authorizes this package to restart the forest
development stack and execute DEVAL In The Details for:

<https://wc.bearhive.duckdns.org/weppcloud/runs/branching-hubbub/disturbed9002_wbt/>

This authority permits the normal report refresh request, RQ job creation,
Docker exec in the existing `weppcloudr` container, and expected writes below
that run's DEVAL export/log paths. It does not authorize deleting or rebuilding
the run, changing forest mounts, restarting other hosts, production promotion,
or any Kubernetes action. Before restart, capture the current Compose render,
mounts, service health, Git revision, and dirty-tree state. If unrelated dirty
state overlaps deployment files, stop rather than overwrite it.

## References

- `docs/schemas/weppcloudr-render-execution-contract.md` - normative behavior
- `docs/dev-notes/weppcloudr-render-execution-contract-review-2026-08-21.md` - design review dispositions
- `wepppy/rq/weppcloudr_rq.py` - current Docker-exec task
- `wepppy/weppcloud/routes/weppcloudr.py` - enqueue and browser workflow
- `wepppy/weppcloud/routes/_run_context.py` - canonical run/active roots
- `docker/docker-compose.dev.yml` - authorized forest stack
- `docker/AGENTS.md` - deployment identity and Compose rules
- `wepppy/rq/job-dependencies-catalog.md` - RQ graph authority

## Deliverables

- Backend implementation and type/test surfaces
- One-shot renderer request-v1 source and tests
- Updated RQ/configuration/operator documentation
- Forest Compose regression evidence
- Completed correctness, QA, and security review artifacts

## Follow-up Work

- Build and publish the digest-pinned Kubernetes renderer/control-plane images.
- Author and review Kubernetes manifests and target-cluster admission/storage
  policy.
- Execute live Kubernetes integration, rollback, and production promotion.
