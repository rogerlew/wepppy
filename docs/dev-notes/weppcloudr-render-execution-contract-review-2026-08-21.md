# WEPPcloudR Render Execution Contract Review — 2026-08-21

## Scope

Independent correctness, security, and QA reviews examined
`docs/schemas/weppcloudr-render-execution-contract.md` before implementation.
This note records disposition; the canonical contract contains the normative
resolution.

## Disposition

| Finding | Severity | Disposition |
| --- | --- | --- |
| RQ worker count is not a hard cap after worker loss | Blocker | Accepted. Worker count is now steady-state backpressure; a separate atomic logical permit enforces `MAX_ACTIVE_RENDERS`, with namespace quota as defense in depth. |
| Task-local cancellation cannot survive RQ workhorse termination | Blocker | Accepted. A narrow out-of-process render control plane owns create, cancel, reconcile, TTL activation, and orphan reaping with durable intent and dispatch locking. |
| RQ-ID identity does not serialize distinct renders of one artifact | Blocker | Accepted. The contract requires an artifact-scoped lock and monotonic publication fencing; input revision is only an additional coherency check. |
| Job TTL can erase state before reconciliation | Blocker | Accepted. TTL is omitted until terminal logs and a durable execution receipt are captured; any creation-time safety TTL requires equivalent durable evidence. |
| Retry semantics were contradictory after terminal failure or TTL | Blocker | Accepted. Same-ID requeue reconciles only; a terminal failure needs a new RQ ID, and a durable receipt distinguishes absent from cleaned state. |
| Whole-`/wc1` Pod mount weakens run isolation | High | Accepted. Render Pods mount the validated canonical run WD by approved PVC `subPath`; whole-volume access requires explicit risk acceptance. PUP scope is not narrower because its supported symlinks depend on parent-run resources. |
| Direct Job creation authority was insufficiently constrained | High | Accepted. The contract selects a narrow control plane, fail-closed admission, fixed digest/entrypoint, restricted RBAC, and explicit forbidden Pod features. |
| Existing Compose implementation was declared conformant prematurely | High | Accepted. Compose is identified as the legacy transport and must close shared hardening gaps before conformance is claimed. |
| Render request/result protocol was underspecified | High | Accepted. A strict 16-KiB version-1 request schema, fixed derived fields, independent renderer validation, and durable execution receipt are now required. |
| Failure categories lacked stable machine codes and precedence | High | Accepted. The contract now maps expected Kubernetes evidence to canonical codes and retry policy, with precedence and sanitized RQ behavior. |
| `skip_cache` pre-deletion conflicts with atomic publication | High | Accepted. The last known-good artifact remains until a validated replacement is atomically published. |
| Renderer lacked required network isolation | Medium | Accepted. Default-deny ingress/egress is mandatory with only documented storage traffic allowed. |
| Renderer secret and workload identity policy was ambiguous | Medium | Accepted. No secrets by default, no token or cloud identity, and admission denial of secret/config injection are required. |
| Run-visible diagnostic logs could leak data | Medium | Accepted. Logs move outside the export tree, default to a 1-MiB per-stream cap, retain the tail with a marker, and have protected modes/content. |
| Source-revision tags were treated as immutable | Medium | Accepted. Production Job specs and admission require an OCI digest; tags are provenance only. |
| Acceptance and configuration bounds were not measurable | Medium | Accepted. Canonical configuration meanings and cross-field timeout, cancellation, concurrency, log, admission, network, TTL, and rollback gates were added. |
| Pre-create receipt could not bind an unknown Kubernetes UID safely | Blocker | Accepted on closure review. A durable creating state, ownership nonce, request/spec digests, ambiguous-create reconciliation, and atomic UID binding now close the crash window. |
| Render-control-plane API lacked authentication and ingress constraints | High | Accepted on closure review. The contract requires internal-only exposure, workload identity, scoped authorization, replay safety, exact RBAC, rate limiting, audit, and negative tests. |
| Fixed writable request file could be replaced or raced | High | Accepted on closure review. Requests are generation-unique, atomically created, read-only mounted, and verified against an independently authenticated digest. |
| Terminal receipt, cancellation polling state, and recovery trigger were incomplete | High | Accepted on closure review. Terminal receipt fields, exact cleanup metadata, same-ID watchdog/retry, and retry-exhaustion behavior are now normative. |
| Input revision was allowed as a stale-writer fence | High | Accepted on closure review. Monotonic publication fencing is mandatory; input revision is only an additional coherency check. |

## Residual Implementation Gates

- The contract is reviewed design, not proof that either backend conforms.
- The implementation package must define the control-plane wire API and durable
  receipt serialization consistent with the contract's fixed authority and
  state fields.
- Admission-policy feasibility for dynamic approved run-WD `subPath` values
  must be proven on the target cluster before implementation is deployable.
- Resource measurements must determine initial CPU, memory, timeout, and
  `MAX_ACTIVE_RENDERS` values; these operational values are intentionally not
  guessed in the contract.
- Compose must close its current unbounded-log, evaluated-expression,
  root-confinement, and final-file verification gaps as part of the shared
  backend refactor.

No finding was rejected. Similar findings from multiple reviews were merged
into single normative resolutions above.
