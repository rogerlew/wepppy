# Correctness Review — WEPPcloudR Execution Backend Refactor

**Review state**: Latest implementation and forest proof reviewed; no material
findings remain

**Gate**: PASS

**Reviewer**: Independent Codex correctness reviewer

**Date opened**: 2026-08-21

**Date re-reviewed**: 2026-08-21

## Scope and Evidence

This review covers the current uncommitted repository-side implementation
against `docs/schemas/weppcloudr-render-execution-contract.md` and the active
ExecPlan. It focuses on Compose parity, Kubernetes lifecycle and recovery,
fencing, cancellation, retry classification, path/artifact semantics, and
regression coverage. Production code was not modified by this review.

Validation and evidence reviewed in the latest pass:

- Focused pytest passed 139 tests across the backend, control-plane, RQ task,
  cancellation, route, and rq-engine suites, with 15 warnings.
- All three R sources parsed in the running `weppcloudr` container;
  `weppcloudR/publish_fenced.py` compiled successfully.
- `git diff --check`, `wctl check-rq-graph`, and `wctl check-test-stubs` passed;
  stub validation retained one preexisting invalid-escape warning.
- No Compose YAML file is modified in the working tree.
- The authorized forest proof passed. Job
  `d77753a7-5505-4a1b-bce3-3008a30d29b7` completed via `docker-exec` in about
  15.7 seconds and produced a 14,077,008-byte HTML artifact with SHA-256
  `2234c3682b0a50c80d9c97920bba4524d67a04f0587d5b418e35bba08b89c1a1`.
  Renderer logs were bounded and mode `0660`; the normalized before/after mount
  snapshots were identical at SHA-256
  `0d6ad8fcf13aa23488bf3a84fecb2236ea2496681b98e8f4a175c42cc4141829`.
  Full evidence is in
  `artifacts/2026-08-21_forest_compose_integration.md`.
- The same authorized container executed the actual `render-request-v1.R`
  entrypoint. A valid digest-bound cache request returned a terminal-success
  receipt bound to the exact RQ ID, request digest, artifact SHA-256/size, and
  fencing generation. Wrong-digest and correctly digested extra-field requests
  both failed with exit code 2, and the temporary request file was removed.
- Post-PASS cancellation regressions prove that cleanup timeout retains the
  permit, owned-Job absence cleans execution files before persisting `CLEANED`,
  a cleanup failure remains unpublished and is retried, cancellation is
  acknowledged once, and terminal stdout/stderr references propagate.
- `weppcloudR/Dockerfile` now explicitly installs the `python3` runtime used by
  the fenced publication helper.

## Latest Patch Disposition

| Concern | Disposition | Current evidence |
| --- | --- | --- |
| Repository-qualified immutable image | Resolved | `build_job_spec()` constructs `repository@sha256:<digest>` and verifies the request snapshot (`wepppy/rq/weppcloudr_control_plane.py:75-83,275-288,319`). |
| PVC mapping and run-root containment | Resolved at the repository interface | Explicit `/wc1` root-to-subpath mappings reject unapproved, root-level, and escaping paths; geodata remains a separate read-only PVC (`wepppy/rq/weppcloudr_control_plane.py:65-69,240-272,341-365`). Deployment still owns the reviewed claim mapping and admission policy. |
| Compose monotonic fencing and forced-cache freshness | Resolved | Fence allocation advances under the publication lock, both R entrypoints use the descriptor-based publisher, and `skip_cache` renders to isolated temporary state before fenced replacement (`wepppy/rq/weppcloudr_rq.py:179-227`; `weppcloudR/render-compose-request.R:72-115`). The forest no-cache render and mount comparison passed. |
| Kubernetes publication identity race | Resolved | Cache identity and new publication are hashed while holding the same fence lock; the helper copies through directory file descriptors and returns the captured identity (`weppcloudR/render-request-v1.R:171-238`; `weppcloudR/publish_fenced.py:55-146`). |
| Publisher crash/failure recovery | Resolved | The helper removes only staging it created and preserves a foreign `O_EXCL` target. An executable test proves foreign-target preservation, cleanup after post-create failure, and a corrected successful retry (`weppcloudR/publish_fenced.py:55-58,105-114,139-146`; `tests/rq/test_weppcloudr_backends.py:330-379`). |
| Durable cancellation reconciliation and grace | Resolved at the state-machine seam | Reconciliation consumes durable intent and publishes the deleting transition without another browser call; cancellation waits for owned-Job absence. Absence performs idempotent execution-file cleanup before persisting `CLEANED`; an injected cleanup failure leaves the receipt `ACTIVE`/deleting and unpublished so the next reap retries it. Cleanup timeout retains the permit and final acknowledgment occurs once (`wepppy/rq/weppcloudr_control_plane.py:773-788`; `tests/rq/test_weppcloudr_control_plane.py:454-539`; `tests/rq/test_cancel_job.py:236-291`). Exact and near-miss no-receipt response schemas are covered (`tests/rq/test_weppcloudr_backends.py:249-290`). |
| Reaper event starvation and loss after cleaned | Resolved | The canonical contract now requires durable acknowledgment and cleaned-unacknowledged eligibility (`docs/schemas/weppcloudr-render-execution-contract.md:209-212`). The reaper acknowledges only after successful publish and isolates each receipt; the test proves later-receipt progress and retry of the first cleaned receipt (`wepppy/rq/weppcloudr_control_plane.py:182-193,549-573`; `tests/rq/test_weppcloudr_control_plane.py:589-637`). |
| Retry classification | Resolved | The legacy Kubernetes shape rejection is inside the classified boundary. Tests cover retryable API failure, exhausted retryable failure metadata, canonical non-retryable failure, explicit retry disabling, and the missing-`run_root` edge (`wepppy/rq/weppcloudr_rq.py:423-425,498-516`; `tests/rq/test_weppcloudr_rq.py:35-99`). |
| Terminal timestamps, bounded diagnostics, and lifecycle | Resolved at the interface | Receipts retain lifecycle timestamps and stdout/stderr references; permit release, TTL activation, Job-absence confirmation, execution-file cleanup, and event acknowledgment are distinct transitions (`wepppy/rq/weppcloudr_control_plane.py:118-172,700-816`; `tests/rq/test_weppcloudr_control_plane.py:497-569`). |
| UID binding, same-ID create recovery, and pending deadline | Resolved | Compare-and-swap recovery, attempt-relative ambiguous-create grace, UID binding, and the Job-relative pending timeout preserve the durable snapshot (`wepppy/rq/weppcloudr_control_plane.py:421-496,575-675`). |
| Kubernetes one-shot R request/result contract | Resolved for package scope | The forest evidence executes the real entrypoint and proves valid digest-bound cached receipt identity plus wrong-digest and extra-field rejection. Automated tests separately cover shared request validation, PUP containment, publisher recovery, and stale fencing (`artifacts/2026-08-21_forest_compose_integration.md`; `tests/rq/test_weppcloudr_backends.py:72-98,320-379`; `tests/rq/test_weppcloudr_rq.py:155-169`; `tests/rq/test_weppcloudr_control_plane.py:640-672`). |
| Renderer helper runtime | Resolved | The image explicitly installs `python3`, which the R entrypoints use to invoke the fenced publisher (`weppcloudR/Dockerfile:32-50`). |

## Closed Findings

### COR-01 — Closed — Reaper delivery is durable and batch-isolated

`ReceiptStore.acknowledge_event()` makes delivery acknowledgment explicit.
`reap()` acknowledges only after `publish()` returns, logs and isolates a
per-receipt failure, and continues the batch. The fake store keeps a cleaned
receipt reaper-eligible until its exact state is acknowledged. The new
failure/retry test proves both later-receipt progress and eventual delivery of
the initially failed cleaned receipt. The authoritative contract records the
same requirement.

### COR-02 — Closed — Reaper-driven cancellation reaches the event seam

Focused tests now prove durable intent drives foreground deletion and publishes
the `deleting` receipt without another cancellation call. Existing cancellation
tests prove that the RQ workhorse is not stopped before owned-Job absence. Once
absence is confirmed, execution files are cleaned before `CLEANED` persistence;
an injected cleanup failure remains recoverable and unpublished until the next
reap succeeds. Cleanup timeout retains the permit, cancellation is acknowledged
once, and exact no-receipt completion and fail-closed near-miss schemas are
covered. The concrete RQ/alert sink remains correctly deferred to the deployment
package.

### COR-03 — Closed — Retry classification includes validation edges

The missing-`run_root` Kubernetes rejection now runs inside the guarded
classification boundary and disables RQ retries. Helper tests distinguish a
retryable API outage, its exhausted terminal form, a canonical non-retryable
failure, and explicit generic retry suppression.

### COR-04 — Closed — The one-shot R contract has executable conformance evidence

The authorized forest container executed `render-request-v1.R` directly with
the canonical run working directory and existing generation-2 cached artifact.
The valid request returned a terminal-success receipt with the exact RQ ID,
trusted request digest, artifact path, SHA-256, byte size, and fencing
generation. A wrong trusted digest and a correctly digested request with an
extra field both exited 2 with the expected fail-closed reason. The temporary
trusted request was removed and the cached artifact and mounts were unchanged
(`artifacts/2026-08-21_forest_compose_integration.md`, "One-Shot Request-v1
Execution").

Together with automated shared-schema, PUP-path, publisher recovery, and stale
fencing tests, this satisfies the package's one-shot repository/integration
acceptance without claiming Kubernetes deployment validation.

## Residual Risk

The Kubernetes classes are intentionally repository-side interfaces, not a
deployed controller. Durable store, Kubernetes API/watch, authenticated HTTP,
event-sink, admission/RBAC, and live PVC implementations remain external
deployment dependencies and require their own conformance evidence. Before
enabling the backend, deployment must also decide whether legacy
`/geodata/weppcloud_runs` working directories are migrated or represented by a
reviewed writable PVC mapping; the default control-plane mappings intentionally
cover only the canonical `/wc1` roots. The direct one-shot R proof is persisted
but not yet an automated test; the deployment package should convert the valid,
wrong-digest, extra-field, wrong-working-directory, and no-cache variants into a
repeatable image/conformance gate.

## Gate Decision

**PASS for the defined repository and forest scope.** COR-01 through COR-04 are
closed, the focused suite is green at 139 tests, the Compose render and mount
proof passed, and the actual one-shot R entrypoint has positive and fail-closed
execution evidence. No Medium or High correctness findings remain. This pass
does not authorize or claim Kubernetes deployment readiness; that requires the
separate live-cluster acceptance defined by the canonical contract.
