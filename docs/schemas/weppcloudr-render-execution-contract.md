# WEPPcloudR Render Execution Contract
> Authoritative contract for dispatching DEVAL report renders from RQ across
> Docker Compose and Kubernetes deployments.
>
> **See also:** `docs/schemas/rq-response-contract.md`,
> `docs/schemas/rq-controller-state-contract.md`, and
> `docs/schemas/nodb-persistence-concurrency-contract.md`.

## Normative Status

- This document is normative for the execution boundary owned by
  `wepppy.rq.weppcloudr_rq`.
- Requirement keywords `MUST`, `MUST NOT`, `SHOULD`, and `MAY` are interpreted
  per RFC 2119.
- This contract defines the selected target behavior. The current Compose
  implementation supplies the legacy Docker-exec transport but is not declared
  conformant to the strengthened shared path, log, invocation, and artifact
  requirements until tests demonstrate conformance. The Kubernetes Job backend
  is not implemented until repository tests and manifests demonstrate
  conformance.
- An implementation change MUST update this contract, its tests, affected
  operator documentation, and the RQ dependency catalog in the same change set.

## Purpose and Scope

The public RQ task and DEVAL artifact contract remain stable while execution is
selected explicitly by deployment:

| Deployment | Required backend | Execution mechanism |
| --- | --- | --- |
| Docker Compose | `docker-exec` | Run `Rscript` in the named, healthy `weppcloudr` container. |
| Kubernetes | `kubernetes-job` | Create or reconcile one isolated Kubernetes Job running the reviewed `weppcloudr` image. |

The contract covers backend selection, common validation, Job identity,
concurrency, storage, timeouts, cancellation, logs, result verification,
failure translation, and workload authority. It does not define report content
or authorize production deployment.

## Stable RQ and Artifact Boundary

- `render_deval_details_rq(runid, config, active_root, *, skip_cache=False,
  run_root=None, ...)` remains the user-visible orchestration task unless a
  separately ratified RQ contract replaces it. New enqueue sites MUST pass the
  canonical `run_root`. A missing value MAY normalize to `active_root` only for
  legacy queued Compose jobs; the Kubernetes backend MUST reject it.
- Existing enqueue, job tracking, UI polling, and StatusMessenger behavior MUST
  continue to use the canonical RQ job ID and response contracts.
- Successful execution MUST return the absolute path to
  `<active_root>/export/WEPPcloudR/deval_<runid>.htm` only after verifying that
  the artifact is a regular, non-symlink file in the approved run tree.
- The legacy `parquet_overrides` keyword MAY remain as an ignored queued-job
  compatibility argument while old jobs can still exist.
- Cached output behavior and `skip_cache` semantics MUST be identical across
  execution backends. `skip_cache` forces a new generation but MUST NOT delete
  the last known-good artifact before its replacement is validated and ready
  for atomic publication.

## Backend Selection

- Selection MUST use one explicit deployment configuration value. The
  canonical values are `docker-exec` and `kubernetes-job`.
- Missing configuration MAY default to `docker-exec` only for existing Compose
  deployments during migration. Kubernetes manifests MUST select
  `kubernetes-job` explicitly.
- Unknown values or an unavailable selected backend MUST fail before execution
  with an actionable configuration error.
- Implementations MUST NOT silently fall back between Docker and Kubernetes.
- Backend-specific configuration MUST NOT leak into the public route or browser
  contract.

## Common Orchestration Responsibilities

Before invoking either backend, the RQ orchestration layer MUST:

1. Resolve the canonical `run_root` working directory and `active_root`; verify
   that `run_root` is an existing descendant of a configured run-root allowlist,
   normally `/wc1/runs`, and that `active_root` is within that WD.
2. Reject retired root resources and path traversal or symlink redirection.
3. Create and confine the export directory beneath `active_root`.
4. Apply `skip_cache` before dispatch without deleting unrelated artifacts.
5. Construct one structured render request containing only required logical
   identifiers, validated paths, cache policy, and correlation identifiers.
6. Publish the existing started status.

After backend completion, the orchestration layer MUST:

1. Persist bounded stdout and stderr diagnostics outside the publicly served
   export tree, under `<active_root>/_logs/weppcloudr/`, using the RQ job ID.
2. Verify the expected output path and reject a symlink or non-regular file.
3. Publish completion only after verification succeeds.
4. Translate expected backend failures into stable, actionable errors and
   publish the existing exception status.

Backends MUST receive argument arrays or a structured request artifact. Shell
command construction and evaluation of caller-provided command text are
forbidden.

### Versioned Render Request

The cross-repository request is a UTF-8 JSON object with no unknown fields and
these required fields:

| Field | Contract |
| --- | --- |
| `schema_version` | Integer `1`. |
| `rq_job_id` | Exact canonical RQ job ID, maximum 64 ASCII characters. |
| `runid` | Validated logical run ID, maximum 245 UTF-8 bytes; `/`, `\`, NUL, `.`, and `..` are forbidden. |
| `config` | Validated configuration identifier, maximum 255 UTF-8 bytes. |
| `run_root` | Canonical absolute run working directory beneath an approved run-root allowlist. |
| `active_root` | Canonical absolute render target within `run_root`; it may be a PUP or scenario directory. |
| `skip_cache` | JSON boolean. |
| `correlation_id` | Non-secret opaque identifier, maximum 128 ASCII characters. |
| `deployment_revision` | Reviewed WEPPpy source revision. |
| `renderer_image_digest` | Exact `sha256:` OCI digest selected for this execution. |

The serialized request MUST be at most 16 KiB. The orchestrator derives the
template, command, namespace, mount, and final output filename; none may be
selected by the request. The host-side request path MUST be generation-unique
from the RQ ID, atomically created without replacement, owned by the run
identity, and mode `0440` or narrower. A Pod mounts only that file read-only at
a fixed in-container pathname. The trusted SHA-256 request digest is delivered
through the authenticated control-plane execution snapshot, independently of
the writable run tree, and the renderer MUST verify the exact bytes and RQ ID
before parsing. The request is removed only during bounded terminal cleanup.
WEPPcloudR owns the versioned parser and one-shot renderer entrypoint, and
incompatible schema versions MUST fail explicitly.

The renderer MUST validate field types, lengths, root confinement, symlinks,
and expected output again after mounts are established and immediately before
publication. The relationship among `run_root`, `active_root`, `runid`,
`config`, and any PUP/scenario context MUST be resolved through the same
canonical RunContext rules used at enqueue; a caller-supplied path alone is not
authority.

## Docker Compose Backend

- Compose deployments MUST retain the existing Docker-exec behavior until a
  separately accepted Compose replacement is implemented.
- The RQ worker MAY mount the Docker socket only where this selected backend is
  enabled and MUST target the configured `weppcloudr` container name.
- The backend MUST use bounded subprocess execution, capture stdout and stderr,
  preserve the child exit status, and verify the final artifact.
- Adding Kubernetes execution MUST NOT require changing the Compose renderer
  image or merging the WEPPpy and WEPPcloudR images.

## Kubernetes Job Backend

### Workload Shape

- One RQ orchestration task MUST own at most one logical Kubernetes render Job.
- Each Job MUST create a fresh Pod that runs a one-shot `Rscript` renderer and
  exits. It MUST NOT start the long-lived Plumber server.
- Production Jobs MUST use the standalone reviewed `weppcloudr` image pinned by
  OCI digest. A source-revision tag is provenance only and MUST be resolved to
  and recorded with its digest before dispatch.
- The render Pod MUST NOT contain the WEPPpy base image, Docker CLI, Docker
  socket, Kubernetes client credentials, or an enabled service-account token.
- The Pod MUST use a non-root security context, `allowPrivilegeEscalation:
  false`, dropped Linux capabilities, `seccompProfile: RuntimeDefault`, and
  explicit CPU and memory requests and limits. Its root filesystem MUST be read
  only; reviewed bounded `emptyDir` mounts provide required R, Pandoc, and
  temporary-file paths.
- Production R dependencies MUST be present in the image. A render MUST NOT run
  `renv::restore()` or mutate a shared package library at job startup.

### Identity and Reconciliation

- Kubernetes Job identity MUST be deterministic from the canonical RQ job ID
  and safe for Kubernetes metadata. User-controlled run IDs and paths MUST NOT
  be copied unescaped into object names or labels.
- On RQ start or retry, the orchestrator MUST first look up the deterministic
  Job identity:
  - absent: create it once;
  - pending or running: reconnect and continue watching;
  - succeeded: collect the recorded result and verify the artifact;
  - failed: collect diagnostics and report the classified failure.
- An RQ retry MUST NOT create a second Job for the same RQ job ID.
- Kubernetes create conflicts and watch disconnections MUST enter the same
  reconciliation path rather than being treated as proof of failure.
- Job specifications MUST carry an application label, RQ job correlation ID,
  and deployment revision. Labels MUST NOT expose secrets or unrestricted run
  paths.
- Before Kubernetes create, the control plane MUST durably record a `creating`
  receipt and acquire the logical admission permit using the RQ ID and an
  unguessable ownership nonce. The Job carries that nonce plus request and spec
  digests. Reconciliation follows these exclusive state rules:
  - `creating` or `create-ambiguous` without a UID: a matching nonce and request
    and spec digests authorize one compare-and-swap UID binding; absence after
    bounded reconciliation authorizes an identical deterministic create retry
    with the same nonce and snapshot;
  - UID-bound `active`, `terminal-success`, `terminal-failure`, or `cleaned`: a
    matching UID, nonce, and snapshot authorize reconciliation; absence never
    authorizes recreation; and
  - any ownership-marker, UID, nonce, request/spec digest, backend, namespace,
    Job-name, image-digest, or deployment-revision mismatch fails closed without
    adopting, deleting, or recreating the object automatically.
- Retries use the recorded execution snapshot rather than current deployment
  defaults. Reconciliation MUST explicitly handle deleting and suspended Jobs,
  an object absent after a recorded UID, and a terminal Job with missing Pod or
  status. With no prior-create receipt, absence authorizes initial creation.
- The durable receipt MUST outlive Kubernetes TTL cleanup and distinguish
  never-created, creating, create-ambiguous, active, terminal-success,
  terminal-failure, and cleaned states. Its terminal record contains artifact
  identity and path, content SHA-256 and byte size, monotonic fencing
  generation, terminal state/reason, renderer image digest, creation/start/end
  timestamps, and bounded-log references. A same-RQ-ID requeue resumes
  reconciliation only. A terminal renderer failure is not automatically
  retried; a new render attempt receives a new RQ job ID.
- Receipt-to-RQ event delivery MUST be durably acknowledged only after the
  event sink accepts the exact receipt state. A cleaned receipt with an
  unacknowledged event remains reaper-eligible, so a delivery outage cannot
  lose terminal or stop coordination and cannot starve later receipts.

### Storage and Paths

- The RQ worker MAY mount shared RWX `/wc1`, but each render Pod MUST mount only
  its validated canonical `run_root` working directory read-write, using an
  approved PVC `subPath`, at the identical absolute WD path supplied by the
  orchestrator. The PUP/scenario `active_root` remains a path inside that mount.
  This WD boundary is intentionally not narrowed further: valid PUP layouts use
  symlinks to parent-run resources, so mounting only `active_root` would break
  supported behavior without a material security benefit. The control plane
  and admission policy MUST independently validate the derived WD `subPath`,
  mount path, and active-root containment. Whole-`/wc1` renderer mounts require
  explicit security risk acceptance and are not the default contract.
- Geodata MUST be mounted read-only at `/geodata` when the renderer requires it.
- UID, GID, umask, and NFS permissions MUST permit atomic publication readable
  by the web and worker services.
- The renderer MUST independently confine input and output paths beneath
  configured approved roots. Validation by the RQ caller alone is insufficient.
- A render MUST write to a generation-unique temporary artifact in the final
  directory and atomically publish the final HTML. Abandoned request and
  temporary files MUST have bounded cleanup.
- RQ-ID reconciliation is not sufficient for two distinct jobs targeting the
  same report. Both backends MUST acquire an artifact-scoped lock keyed by the
  canonical active root and report identity. Publication MUST use a monotonic
  fencing token so a stale, superseded, or duplicate Pod cannot overwrite a
  newer generation. An input revision is an additional coherency check, not a
  replacement for fencing. Lock release MUST verify ownership and stale-lock
  recovery MUST be bounded.

### Concurrency and Admission

- A dedicated RQ queue MUST carry Kubernetes WEPPcloudR orchestration tasks.
- Dedicated RQ worker-process count is the normal steady-state admission and
  backpressure mechanism. Because an orphaned render may survive worker loss,
  worker count alone is not a hard concurrency cap.
- General-purpose RQ worker capacity MUST NOT be consumed by waiting render
  orchestrators.
- Before Job creation, the Kubernetes control plane MUST enforce configured
  `max_active_renders` through an atomic recoverable logical permit. The permit
  begins with the RQ ID and ownership nonce and binds to the Job UID after
  creation; it is released only after terminal Pod termination. A dedicated-
  namespace `ResourceQuota` mathematically sized to the fixed per-render
  request and a `LimitRange` remain mandatory defense in depth, but neither
  replaces logical admission.
- The initial implementation MUST NOT require Kueue. Adding cluster-wide batch
  admission or priority policy requires a separate contract decision.
- Backlog MUST remain in Redis/RQ rather than being expanded eagerly into an
  unbounded number of pending Kubernetes Jobs.

### Retry, Timeout, and Cancellation

- The initial Kubernetes Job policy MUST use `backoffLimit: 0`; RQ owns
  application retry decisions.
- Kubernetes `activeDeadlineSeconds` MUST be shorter than the outer RQ timeout,
  and the outer timeout MUST be at least the active deadline plus the configured
  terminal-collection budget.
- RQ retry policy MUST consider rendering idempotent only through deterministic
  Job reconciliation and atomic output publication.
- Kubernetes orchestration jobs MUST have a bounded same-ID recovery mechanism,
  using RQ Retry or a dedicated watchdog, for abnormal workhorse loss and
  retryable control-plane failures. Recovery MUST NOT depend on browser refresh.
  Retry exhaustion preserves the receipt for controlled operator recovery.
  `weppcloudr_k8s_api_unavailable` becomes terminal only after exhaustion; a
  scheduled same-ID recovery MUST NOT retain terminal `job.meta.error`.
- Cancellation MUST be linearized with creation through a durable cancellation
  intent and dispatch lock. The creator checks intent before creation and again
  while holding the lock. Cancellation persists intent before requesting Job
  deletion with foreground propagation.
- Cancellation and orphan cleanup MUST be owned outside the killable RQ
  workhorse by the narrow render control plane. Worker-local `finally` cleanup
  is insufficient. The cancellation endpoint persists
  `job.meta.render_cleanup_state="deleting"`, returns accepted, and requests
  foreground deletion. The RQ stop command MUST NOT be sent until owned Pod
  absence is confirmed. Confirmation permits
  `render_cleanup_state="complete"`, followed by the stop command and terminal
  cancellation. Grace expiry sets
  `render_cleanup_state="cleanup_timeout"`, does not stop the RQ workhorse,
  leaves orchestration nonterminal, alerts operators, and remains owned by the
  reaper; it MUST NOT report successful cancellation while an owned Pod remains.
- Loss of the RQ worker or Kubernetes watch connection MUST NOT be interpreted
  as cancellation; a replacement task MUST reconcile existing state.
- Jobs MUST initially omit an active completion TTL. After terminal status,
  bounded logs, and the execution receipt are durable, the control plane MAY
  patch in `ttlSecondsAfterFinished` or delete the Job. A creation-time safety
  TTL is permitted only when durable cluster logging and the execution receipt
  preserve all information needed for reconciliation.

### Result and Failure Contract

- Pod logs and termination status MUST be collected before TTL cleanup.
- Each persisted stdout or stderr file MUST be at most the configured byte cap,
  which defaults to 1 MiB. Truncation retains the tail and prepends an explicit
  marker. Files MUST be written without control-character injection, with mode
  no broader than `0660`, under the run owner/group, and with the same retention
  as other protected run logs. Job specs, environment dumps, Kubernetes events,
  tokens, credentials, and unsanitized paths MUST NOT be persisted there.
- Expected failures MUST populate canonical `job.meta.error` and `error_id`;
  open RQ surfaces return `exc_info=null`. The initial mapping is:

| Evidence | Canonical code | Retry policy |
| --- | --- | --- |
| API unavailable after bounded reconnect | `weppcloudr_k8s_api_unavailable` | Retry reconciliation. |
| API authorization denial | `weppcloudr_k8s_unauthorized` | Do not retry automatically. |
| Admission or quota rejection | `weppcloudr_k8s_admission_rejected` | Do not retry automatically. |
| Pending-start deadline exceeded | `weppcloudr_k8s_unschedulable` | New RQ attempt after operator policy permits. |
| Image pull terminal failure | `weppcloudr_k8s_image_pull_failed` | Do not retry automatically. |
| PVC mount terminal failure | `weppcloudr_k8s_volume_mount_failed` | New RQ attempt after storage recovery. |
| Pod eviction | `weppcloudr_k8s_evicted` | New RQ attempt. |
| Container `OOMKilled` | `weppcloudr_k8s_oom_killed` | Do not retry without resource change. |
| Job active deadline | `weppcloudr_k8s_deadline_exceeded` | Do not retry automatically. |
| Renderer nonzero exit | `weppcloudr_renderer_failed` | Do not retry automatically. |
| Successful exit with invalid artifact | `weppcloudr_artifact_invalid` | Do not retry automatically. |
| Recorded execution whose state cannot be reconstructed | `weppcloudr_k8s_state_lost` | Fail closed for operator reconciliation. |

Terminal container reason takes precedence over a generic exit code; OOM takes
precedence over generic renderer failure, and artifact validation occurs only
after a successful renderer exit. A transient watch disconnect is not terminal
until bounded reconnect/reconciliation fails.
- Kubernetes diagnostic detail exposed through user-facing RQ surfaces MUST be
  sanitized according to `docs/schemas/rq-response-contract.md`. Full internal
  detail belongs in structured operator logs keyed by the RQ job ID or error
  correlation ID.

## Kubernetes Authority Boundary

- General-purpose RQ workers MUST NOT receive cluster-wide workload creation
  privileges.
- A narrow internal render control plane, running outside the killable RQ
  workhorse, MUST own Job creation, reconciliation, cancellation, log
  collection, TTL activation, and orphan reaping. RQ tasks retain application
  orchestration and wait on this control plane. General RQ workers MUST NOT
  hold Kubernetes workload-creation credentials.
- The control plane MUST be exposed only through an internal ClusterIP with no
  Ingress or public proxy. Default-deny ingress policy allows only the dedicated
  render-orchestrator workers. Calls require authenticated workload identity
  with an explicit audience; authorization binds caller identity, operation,
  canonical RQ job ID, active-root scope, and request digest. Mutation requests
  MUST be replay-safe and idempotent. Denied identity, replay mismatch,
  cross-run access, and admission saturation MUST be rate-limited and audited.
- The control plane MUST accept only the versioned render request and MUST NOT
  allow callers to specify an arbitrary image, command, volume, service
  account, namespace, resource envelope, or Kubernetes metadata.
- Its dedicated namespace Role MUST omit `pods/exec`, `pods/attach`,
  `pods/portforward`, secret reads, RoleBinding changes, and admission-policy
  mutation. Its positive RBAC allowlist is Jobs `create,get,list,watch,patch,
  delete`, Pods `get,list,watch`, and `pods/log` `get`, all in the renderer
  namespace; wildcard resources or verbs are forbidden.
- A fail-closed validating admission policy, controlled by an identity the
  render control plane cannot modify, MUST allow exactly one digest-pinned
  container with the fixed entrypoint and approved resources. It MUST reject
  init, ephemeral, and sidecar containers; `hostPath`; host network/PID/IPC;
  privilege or added capabilities; privilege escalation; alternate service
  accounts; projected API tokens; `envFrom`; secret or ConfigMap references;
  unapproved PVCs/subpaths; and mutable image references. If the cluster cannot
  enforce this policy, Kubernetes rendering MUST remain disabled.
- Render Jobs receive no application secret by default. They use a dedicated
  service account with no RoleBinding or cloud-workload-identity binding and
  `automountServiceAccountToken: false`. A required secret needs a separately
  reviewed contract amendment and explicit admission allowlist.
- Renderer Pods MUST be selected by default-deny ingress and egress
  NetworkPolicies. Only documented storage traffic needed by the PVC provider
  MAY be allowed. Kubernetes API, cloud metadata, unrelated cluster services,
  and external egress MUST remain denied.
- Routine rendering MUST NOT use Kubernetes `pods/exec`. Pod exec grants
  arbitrary command execution, bypasses per-render scheduling and resource
  accounting, and cannot be restricted by standard RBAC to the approved R
  command. Pod exec is reserved for separately authorized operator diagnostics.

## Configuration Surface

The authoritative runtime configuration schema MUST define and validate at
least these canonical names:

| Name | Meaning |
| --- | --- |
| `WEPPCLOUDR_EXECUTION_BACKEND` | `docker-exec` or `kubernetes-job`. |
| `WEPPCLOUDR_CONTAINER` | Compose renderer container name. |
| `WEPPCLOUDR_COMMAND_TIMEOUT` | Compose execution timeout. |
| `WEPPCLOUDR_K8S_QUEUE` | Dedicated Kubernetes render orchestration queue. |
| `WEPPCLOUDR_K8S_NAMESPACE` | Dedicated renderer namespace. |
| `WEPPCLOUDR_K8S_IMAGE` | Digest-pinned renderer reference. |
| `WEPPCLOUDR_K8S_MAX_ACTIVE_RENDERS` | Hard admitted-render bound. |
| `WEPPCLOUDR_K8S_PENDING_TIMEOUT` | Maximum wait for Pod start. |
| `WEPPCLOUDR_K8S_ACTIVE_DEADLINE` | Job execution deadline. |
| `WEPPCLOUDR_K8S_TERMINAL_BUDGET` | Log, verification, and cleanup interval. |
| `WEPPCLOUDR_K8S_CANCEL_GRACE` | Maximum cancellation confirmation interval. |
| `WEPPCLOUDR_K8S_COMPLETED_TTL` | TTL applied after durable collection. |
| `WEPPCLOUDR_LOG_MAX_BYTES` | Per-stream persisted log limit; default 1 MiB. |

The schema also defines approved run roots, PVC and `subPath` mapping,
read-only geodata PVC, renderer service account, fixed resource requests and
limits, controller endpoint/identity, and optional node selector, affinity, and
tolerations. Invalid cross-field values MUST fail startup. In particular, outer
RQ timeout must be at least active deadline plus terminal budget, and the hard
admission mechanism must be consistent with `MAX_ACTIVE_RENDERS`.

Secrets MUST use the established runtime secret mechanism and MUST NOT be
placed in Job arguments, environment literals, labels, annotations, or logs.

## Deployment and Rollback

- Compose and Kubernetes backends MUST have independent conformance tests.
- Kubernetes acceptance requires an unmocked render using deployed RWX storage,
  artifact readback through the WEPPcloud route, cancellation, timeout, worker
  interruption/reconciliation, and concurrency-cap evidence.
- Acceptance MUST kill an orchestrator during an active render and prove that
  admitted/running Pods never exceed `MAX_ACTIVE_RENDERS`; cancel across the
  create race and prove no owned Pod remains after `CANCEL_GRACE`; verify each
  log is at or below `LOG_MAX_BYTES`; reject malicious Job mutations; and prove
  reconciliation from the durable receipt after Job TTL cleanup.
- Acceptance MUST exercise crash and ambiguous-response windows before and
  after Kubernetes create, verify the ownership nonce/UID binding, reject a
  replaced or digest-mismatched request file, and prove same-ID watchdog
  recovery without browser activity.
- Control-plane acceptance MUST reject unauthenticated, wrong-identity,
  replay-mismatched, and cross-run requests and verify the exact positive RBAC
  allowlist without wildcard authority.
- Network-policy acceptance MUST prove denial of Kubernetes API, cloud metadata,
  unrelated service, and external egress from a renderer Pod while required
  storage and report publication remain functional.
- Deployment MUST begin with a bounded forest rollout before production.
- Rollback MUST stop new enqueue, drain or explicitly cancel the dedicated
  queue, reconcile active Jobs and receipts, and only then scale down the render
  control plane. It changes the explicit backend selection and deployment
  revision and MUST NOT silently switch a running Kubernetes task to Docker
  exec.
- Existing cached HTML remains valid across backend changes when it passes the
  common artifact checks.

## Decision Record

- **Decision:** Preserve Docker exec for Compose and use RQ-wrapped Kubernetes
  Jobs for Kubernetes. **Rationale:** this minimizes Compose regression risk,
  keeps the R image separate, and gives Kubernetes renders isolated resources
  and observable lifecycle state.
- **Decision:** Use dedicated RQ worker count for steady-state backpressure and
  a separate Kubernetes admission bound for the crash-safe concurrency cap.
  **Rationale:** demand remains queued in Redis while orphaned Jobs cannot
  exceed the configured safety bound after worker loss.
- **Decision:** Use a narrow out-of-process render control plane for Kubernetes
  lifecycle authority. **Rationale:** cancellation and orphan cleanup cannot be
  guaranteed by the RQ workhorse that the stop operation terminates.
- **Rejected for routine rendering:** Kubernetes pod exec, because it grants
  arbitrary remote execution and does not create a schedulable, independently
  observable workload.
- **Deferred:** internal HTTP RPC, because a single Plumber process serializes
  long renders and synchronous requests require additional concurrency and
  retry semantics.
- **Deferred:** a dedicated R-native/RQ renderer, because the current Python
  callable imports WEPPpy and a lean worker would require a new independently
  versioned task package or two-container protocol.

## Compliance Checklist

Before enabling `kubernetes-job`:

1. Ratify an implementation work package and security review.
2. Preserve the RQ enqueue, polling, cache, status, and artifact contracts.
3. Prove deterministic create/reconcile behavior across worker interruption.
4. Prove steady-state RQ backpressure and the hard admission cap across worker
   death, retries, and orphan reconciliation.
5. Enforce namespace quota, fail-closed admission, network isolation, non-root
   execution, and no renderer service-account token.
6. Exercise cancellation and every listed failure class that can be induced in
   a test cluster.
7. Verify artifact locking/fencing, atomic output, scoped mounts, and bounded
   protected logs on the production-equivalent RWX volume.
8. Update `wepppy/rq/job-dependencies-catalog.md` and run
   `wctl check-rq-graph` if enqueue routing or dependency edges change.
9. Update Compose, Kubernetes, configuration, operator, and renderer
   documentation in the implementation change set.
10. Complete forest validation before separately authorized production
    promotion.
