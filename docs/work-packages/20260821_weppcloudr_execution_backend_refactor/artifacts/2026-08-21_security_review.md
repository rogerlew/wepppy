# Security Review — WEPPcloudR Execution Backend Refactor

**Review state**: Complete for the current working tree at `822bdfa29fac`

**Gate**: PASS for repository scope; Kubernetes deployment remains disabled

**Reviewer**: Independent dedicated security reviewer

**Date reviewed**: 2026-08-21

## Scope and Threat Model

This review covers the uncommitted Compose and Kubernetes execution work
against `docs/schemas/weppcloudr-render-execution-contract.md`: request and
command construction, run/PVC paths, symlink and time-of-check/time-of-use
safety, artifact publication and fencing, receipt ownership, cancellation,
logs, workload identity, and the Kubernetes authority boundary. This review
changed only this artifact, not production code.

The review assumes concurrent processes can change a shared run tree, an RQ
workhorse can die at any instruction boundary, Docker exec can outlive its
local CLI connection, and internal requests or responses may be malformed.
Kubernetes images, manifests, adapters, and live cluster controls are outside
this package; their mandatory preconditions are recorded separately below.

## Gate Summary

- No unresolved Medium or High repository security findings remain after the
  final remediation wave.
- Focused validation passed (`128 passed`, 14 warnings), and
  `git diff --check` passed.
- The Kubernetes backend is repository-side interface/state-machine work only.
  It must remain disabled until the separate deployment package implements and
  proves all controls in **Deferred Kubernetes Deployment Blockers**.
- Result: PASS for this package's security-review gate. This does not authorize
  a Kubernetes image build, manifest application, or cluster rollout.

## Finding Disposition

| Finding | Final disposition |
| --- | --- |
| Broad or arbitrary PVC mount | Closed. Explicit absolute-root-to-PVC mappings reject the approved root itself, traversal, mapping ambiguity, and active-root escape. The Job mounts only the derived run-WD subPath. |
| Shared-tree symlink/TOCTOU redirection | Closed for the repository boundary. Rendering writes only to isolated `/tmp`; the trusted publisher walks the run tree through directory descriptors with `O_NOFOLLOW`, copies to an `O_EXCL` destination, holds the shared fence lock through copy/hash/publication, and handles cached identity under that lock. Worker log and artifact operations walk child directories from an active-root descriptor, and web readback does the same while requiring a regular final file. |
| Incomplete fencing and stale completion | Closed at repository-interface level. Compose allocates a monotonic generation under the same artifact publication lock. The result carries independently verified RQ ID, request digest, and fencing generation. Durable-store and crash evidence remain deployment requirements. |
| Cancellation crash/reconciliation race | Closed at state-machine level. Intent becomes durable and is reflected in the receipt before UID binding; reaping reissues exact-UID foreground deletion and retains cleanup ownership and its permit through absence or timeout. |
| Bare image digest in `containers[].image` | Closed. Configuration validates repository and bare digest separately, while the Job uses `repository@sha256:digest`. Admission still must restrict the reviewed registry and repository. |
| Incomplete receipt ownership | Closed. Receipts fail closed on namespace, Job name/UID, nonce, request/spec/image/deployment snapshots, result identity, and fencing generation. The no-UID path is limited to the explicit never-created cancellation invariant. |
| Unbounded or raw controller logs | Closed at interface level. Job observations and receipts carry protected log references rather than inline Pod streams; Compose files remain byte-capped, sanitized, non-symlink regular files with mode `0660`. |
| Nonterminal failure releases hard permit | Closed. Pending timeout, suspension, and unexpected deletion begin exact-UID foreground cleanup and retain the permit until Job absence. |
| Unvalidated control-plane request or namespace | Closed. The controller validates the versioned request before store access, binds durable receipts to its configured namespace, and the RQ client requires the same expected namespace. |

## Security Evidence

### Structured invocation and backend isolation

- Compose sends JSON on stdin to a fixed `docker exec -i ... Rscript
  /srv/weppcloudr/render-compose-request.R` argv. Caller data is never evaluated
  as R source (`wepppy/rq/weppcloudr_backends.py:171-227`).
- Backend selection is explicit, incomplete Kubernetes configuration fails
  closed, and there is no Docker/Kubernetes fallback
  (`wepppy/rq/weppcloudr_rq.py:275-298`).
- General RQ workers use only the narrow HTTPS client surface; no Kubernetes
  SDK or cluster credential is present in the worker backend.

### Paths, artifacts, and fencing

- The R adapters render into container/Pod-private `/tmp`, not the shared run
  tree (`weppcloudR/render-compose-request.R:84-98` and
  `weppcloudR/render-request-v1.R:200-211`).
- `publish_fenced.py` walks from a configured approved root with directory
  descriptors, rejects symlink components, verifies the regular source and
  fence, copies to an exclusive destination, hashes while copying, and renames
  under the artifact-scoped lock. Cached identity uses the same locked regular
  descriptor (`weppcloudR/publish_fenced.py:40-133`).
- Worker log writes and artifact validation/hash walk `_logs/weppcloudr` and
  `export/WEPPcloudR` through per-component directory descriptors
  (`wepppy/rq/weppcloudr_rq.py:151-188` and `:301-354`).
- Web readback walks `export/WEPPcloudR` from the active-root descriptor,
  rejects symlinks at every child, and checks the final descriptor is regular
  before reading (`wepppy/weppcloud/routes/weppcloudr.py:601-629`).

### Job and receipt authority

- PVC mapping rejects unapproved roots, root-level mounts, traversal, ambiguous
  mappings, and an `active_root` outside `run_root`
  (`wepppy/rq/weppcloudr_control_plane.py:245-277`).
- The fixed Job uses a digest-pinned standalone image, fixed command, scoped
  run mount, read-only geodata, bounded resources, no service-account-token
  mount, non-root execution, no privilege escalation, dropped capabilities,
  seccomp, and a read-only root filesystem
  (`wepppy/rq/weppcloudr_control_plane.py:280-385`).
- Receipt reconciliation binds immutable namespace, Job name/UID, nonce,
  request/spec/image/deployment snapshots, parsed result identity, and monotonic
  fencing generation (`wepppy/rq/weppcloudr_control_plane.py:613-815` and
  `wepppy/rq/weppcloudr_backends.py:328-459`).
- Cancellation response handling does not stop the RQ workhorse until the
  controller reports deletion complete; timeout remains owned and visible
  (`wepppy/rq/cancel_job.py:36-92`).

## Deferred Kubernetes Deployment Blockers

These controls are outside this repository refactor's authorized deployment
scope. They are not repository findings, but each is a hard precondition for
setting `WEPPCLOUDR_EXECUTION_BACKEND=kubernetes-job`:

1. Implement and independently review the durable receipt/request/fence store,
   Kubernetes gateway, authenticated HTTP server, protected-log collector,
   reaper, RQ event sink, audit trail, and rate limits. The current repository
   provides protocols and a pure state machine, not a deployable control plane.
2. Bind authenticated workload identity with an explicit audience to operation,
   canonical RQ ID, request digest, and active-root scope. The current HTTP
   token handling is not ready for normal rotating projected-token layouts: it
   rejects a symlink at construction and later reopens the pathname
   (`wepppy/rq/weppcloudr_backends.py:243-275`). Select and test a rotation-safe,
   descriptor-validated identity mechanism before deployment.
3. Supply the exact namespace Role/RBAC allowlist, fail-closed validating
   admission policy, renderer service account with no bindings or token,
   default-deny NetworkPolicies, ResourceQuota, LimitRange, approved PVC and
   subPath mappings, read-only geodata, and internal ClusterIP-only exposure.
4. Restrict admission to the reviewed registry/repository and immutable digest,
   build/sign/review the standalone renderer and controller images, and prove
   the Pod spec cannot be mutated to add alternate commands, containers,
   mounts, credentials, or network authority.
5. Capture unmocked RWX/NFS, request replacement, cancellation/create race,
   timeout, worker-loss reconciliation, same-ID recovery, TTL cleanup,
   concurrency-cap, log-bound/redaction, malicious mutation, and network-denial
   evidence before a bounded forest Kubernetes rollout.

Until these controls close, Kubernetes rendering remains non-deployable even
though the repository security gate passes.

## Residual Low-Risk and Defense-in-Depth Notes

- Host helpers begin by opening the already canonical `active_root` pathname,
  then protect all run-internal components with directory descriptors. Walking
  from the configured approved-root descriptor as the first anchor would also
  defend against replacement of an active-root ancestor. This is defense in
  depth under the current authority model, where callers cannot rename run-root
  ancestry.
- The publisher's exclusive `.publishing` file is fail-closed if an abandoned
  name remains. The future cleanup-store adapter should remove owned abandoned
  staging files on bounded terminal cleanup and prove crash recovery.
- Add executable publisher tests for successful copy/hash/publication, cached
  identity, intermediate symlink replacement, and abandoned exclusive staging.
  Existing focused tests cover stale fencing and static path rejection; live
  RWX/NFS race evidence remains mandatory in the deployment package.

## Validation Evidence

The reviewer ran:

```text
wctl run-pytest tests/rq/test_weppcloudr_backends.py \
  tests/rq/test_weppcloudr_control_plane.py \
  tests/rq/test_weppcloudr_rq.py tests/rq/test_cancel_job.py \
  tests/microservices/test_rq_engine_jobinfo.py \
  tests/weppcloud/routes/test_deval_loading.py
```

Result: `128 passed, 14 warnings in 11.42s`.

`git diff --check` also passed.

## Gate Decision

**PASS for repository scope.** No Medium or High security findings remain in
the implementation included by this package. This pass does not authorize
Kubernetes deployment: the backend must remain disabled until a separately
reviewed deployment package closes every control above with live evidence.
