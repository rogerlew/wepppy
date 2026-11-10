# Security review — Declarative DEM vertical slice

## Review status and scope

Reviewer: `/root/dem_contract_security` (independent `security_reviewer`).
Date: 2026-11-10. Security impact: **high**; dedicated review required.
Contract ancestor: `d6e101ab8`; implementation reviewed in the working tree.
This replaces the unperformed-review scaffold with actual findings and evidence.

**Local security findings: closed; zero open high/medium findings.** Contract review
passed after SEC-C1/C2 amendments before implementation. The closing implementation
recheck confirms SEC-I1–I5 remediation. Final release disposition still follows
correctness/QA review and the required environment evidence; those gates are not
substituted by this report. No image publication/live deployment authorization or
risk acceptance is recorded.

Reviewed application scope: `wepppy/declarative/`, `tools/declarative_dem.py`,
NoDb mutation/read-only guards, Flask/rq-engine admission, RQ execution and direct
task guards, Bootstrap, and canonical archive/restore changes. Reviewed deployment
drafts: `/tmp/declarative-deploy-prep/templates/declarative-dem-pod.json` and
`/tmp/declarative-deploy-prep/scripts/render-declarative-dem.py`. Those temporary
artifacts are preparation material, not deployed or durable infrastructure changes.

Canonical authority: [DEM v1 contract](../../../schemas/declarative-dem-v1-contract.md),
[contract decision](20261110_contract_decision.md), and the cross-linked NoDb,
RQ, UI, Bootstrap and catalog contracts. Required generated-artifact and normal
browse/archive evidence remains in the [validation ledger](validation_matrix.md).

## Findings and disposition

| ID | Severity | Finding | Disposition and evidence |
| --- | --- | --- | --- |
| SEC-C1 | High | Project-local publication locking alone permits stale publication across restore. | Contract resolved before implementation: stable catalog lifecycle guard, identity/incarnation revalidation, and refusal during active/uncertain execution. Implementation uses that guard plus publication locking; observation replacement refusal has a direct regression. |
| SEC-C2 | Medium | Incoming declarative archive identity and fence continuity were unspecified. | Contract resolved before implementation: same-build identity/records/hashes before deletion; preserve provenance and READONLY through interrupted restore. Canonical restore and fault tests added. |
| SEC-I1 | High | Raw ZIP-name validation allowed a second normalized path to overwrite a hash-validated DEM; directory-mode restore could alter the preserved provenance fence. | Code corrected: validate normalized targets, reject duplicates/noncanonical paths and extra protected artifacts, detect incoming aliased markers on ordinary projects, exclude provenance directory modes. Canonical archive tests cover aliases, extra files and interrupted restore. |
| SEC-I2 | High | Runtime template comparison omitted executable lifecycle hooks and probes. | Code corrected: compare lifecycle, startup/liveness/readiness probes and volumeDevices; defaults normalized only for known probe fields. Focused negative tests passed. |
| SEC-I3 | Medium | New exception-decorator guard interpreted migration/GC positional filesystem paths as run IDs. | Code corrected: bind the named `runid` argument; non-run operations remain unchanged. Positional migration/GC regression passed. |
| SEC-I4 | Medium | Direct subcatchment/stage task calls could write before reaching a NoDb lock. | Code corrected: explicit task guards added to subcatchment and stage entry points. Direct subcatchment/stage rejection regression passed. |
| SEC-I5 | Medium | Runtime verifier ignored reviewed resource limits and scheduling selection, and omitted node identity from retained evidence. | Resolved after reproduced failure: compare resources and nodeSelector/affinity/scheduler/runtimeClass/priority, check observed Node labels against reviewed selector, and retain strict `node_name` identity. Closing direct reproduction accepts the approved template and refuses both altered limits and unexpected placement; focused regression passed. |

## Threat model and surface assessment

- Operator CLI, reviewed approval file/template, Kubernetes control plane, approved
  image and existing deployment credentials are trusted. The public model definition
  cannot select code, mounts, commands, credentials, paths or arbitrary URLs.
- Public source/public-project admission is explicit. The existing elevation service
  remains unauthenticated; this review grants no private-project/source capability.
- New metadata is additive. Missing marker and empty provenance directory preserve
  ordinary project behavior; malformed/empty/symlinked marker denies mutation.
- Admission owns the project before science. Fixed job IDs, queue binding and durable
  exclusive claims deny duplicate scientific execution; missing/uncertain work
  cannot authorize replay. Terminal RQ state alone does not prove killed-child cleanup.
- Backend and direct-task guards protect scientific state; controls alone are not
  authority. NoDb read-only clearing, public-state changes and Bootstrap reject
  before mutation. Operational archives/logs remain bounded exceptions.
- Git uses explicit paths, disabled hooks/signing/fsmonitor, sanitized Git environment
  and restricted local repository configuration; no remote transport or raster blobs.
  Atomic publication and symlink refusal are exercised on actual files.
- Container draft keeps UID 1000/GID 993, non-root, dropped capabilities, read-only
  root filesystem, read-only geodata/secrets, and disabled service-account tokens.
  It adds one dedicated queue/Pod without changing ordinary queues. Capacity and
  actual mount/identity/umask parity remain deployment evidence requirements.
- External access reuses the existing fixed WMESQUE source resolver. No new dependency,
  public submission endpoint, secret-management system or cluster privilege is added.
- Results/records retain fixed sanitized errors instead of provider/database exception
  text. Existing ordinary exception logging is unchanged; runtime logs still require
  normal access and sanitation before package retention.

## Reviewer-run validation

`wctl run-pytest tests/rq/test_declarative_dem.py
 tests/rq/test_declarative_dem_integration.py --maxfail=1`
passed **22 tests** in 16.41 seconds, with 12 dependency/RQ deprecation warnings.
This exercises actual Git/filesystem/raster boundaries, direct policy and Bootstrap
refusal, the real RQ failed registry, and a fixture-backed adapter/NoDb/finalizer/view
flow. The source acquisition, owner database registration and Kubernetes identity
in that lifecycle test are fixtures; it is explicitly not cluster/source evidence.

Reviewer also reproduced SEC-I5 with the staged Pod template and direct `observe()`
invocation: unexpected node/resource limits were accepted and node identity absent.
`wctl run-pytest tests/rq/test_project_rq_archive.py -k declarative --maxfail=1`
passed **6 tests**, 56 deselected, in 9.69 seconds. This exercises actual canonical
archive creation/restoration, protected-byte retention, extra/aliased member refusal,
and interrupted restore fence retention. Scoped documentation lint also passed.

Closing SEC-I5 verification repeated the direct staged-template experiment after
remediation: the approved template passed and retained `worker-dell-01`; independently
altered limits and frontend-node placement both raised `AdmissionError`.
`wctl run-pytest tests/rq/test_declarative_dem.py -k runtime_rejects --maxfail=1`
passed **1 test**, 21 deselected, in 8.89 seconds. No live Pod was involved.
The staged renderer produced Pod, definition, approvals, ConfigMap and kustomization
artifacts under `/tmp/dem-security-render-check` using a synthetic all-`a` digest,
which is test input only and does not approve a published execution image.

## Remaining release evidence

Final release review must inspect the final revision after correctness/QA
disposition. Retain cancellation, worker interruption, checkpoint
publication failure and finalization-failure results, including truthful outcomes
and no replay. Finish ordinary API/Bootstrap parity and scoped/broad required gates.

The target deployment must retain approved published platform digest, actual Pod/
container/worker binding, selected node/capacity, identities/mounts/umask, real DEM
acquisition/readback, normal authorized browse/download, archive/restore, and the
fresh zero-write elevation result. Unavailable cluster evidence keeps the package
open. Neither mocked Pod data nor this review supplies live-change authorization.

## Receiving deployment preparation review

The staged operations runbook and receiving package/tracker were independently
reviewed before infrastructure-repository transfer. **Static preparation PASS**;
no additional medium/high findings. Scope is inactive files only, with no new
RBAC, Flux application, ingress or service. Copying reviewed preparation does not
activate resources or approve a candidate image.

The runbook correctly accounts for the parent app image transformer and requires
the dedicated worker, definition, approval entry and candidate fleet to agree.
It forbids admission until all guard consumers are healthy and affected writers
are settled, preserves ordinary compute slots, and requires an explicit deployment
window. Recovery retains project/provenance/READONLY and a compatible guard-bearing
image; reverting to pre-feature images while serving declarative projects is
explicitly prohibited. Capacity, runtime imageID representation and actual access/
artifact evidence remain receiving gates.

Reviewed preparation SHA-256 identities (relative to `/tmp/declarative-deploy-prep`):

| File | SHA-256 |
| --- | --- |
| `templates/declarative-dem-pod.json` | `c0852101b51aeaec63a8b06667a36a5dd6a01276beb7055c5db6573c8d741653` |
| `scripts/render-declarative-dem.py` | `b210e500516b403f1050d122476c57c187e03897c2875805793051bcf5287f6f` |
| `docs/operations/declarative-dem-canary.md` | `b12401d697be1f7a5303d0bc9d1704a2b3bb4e0d7b60f180fd80e8e953debce0` |
| `docs/work-packages/20261110-declarative-dem-canary/package.md` | `581c4a5fc496db40f30fe8f0803560d2006c571f88bac0d9104335fa05344a8f` |
| `docs/work-packages/20261110-declarative-dem-canary/tracker.md` | `b5c5cfc3a6cad747ff9c04af4857d2c3ee563f73ff6a599829a1cb9864a78447` |

These hashes identify the preparation reviewed here. The final published candidate,
rendered overlay and live target still require the receiving deployment review.

## Sign-off

Contract checkpoint: approved after SEC-C1/C2 fixes.
Local implementation security recheck: **PASS**, zero open high/medium findings.
Final release/package closure remains pending correctness/QA disposition and
production-equivalent evidence. Reviewer made no implementation or infrastructure
repository changes and performed no live deployment.
