# Complete the declarative DEM vertical slice on open-wepp-org


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Maintain
Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective.
Execution authorized on 2026-11-10 through deployment-ready handoff. Keep the
package tracker synchronized. Live deployment and cluster acceptance are deferred
to the receiving operator; no live cluster changes have happened.

## Purpose / Big Picture


An operator submits a small model definition that selects an approved execution
image and acquires a DEM (a terrain elevation raster). An independent engine runs
the existing RQ task in that image on open-wepp-org, records what actually ran and
what data was observed, then protects the normal project as read-only. A user can
open it and trigger a real derived viewing task without changing the protected
model inputs, outputs or history. This must work end to end, not only as a mocked
unit test. Production wepp.cloud remains out of rollout scope.

## Progress


- [x] (2026-11-10 20:18 UTC) Scaffold plan and evidence/review records.
- [x] M1 discovery, canonical amendments, two independent reviews and ancestor `d6e101ab8`.
- [x] M2 shared task provenance with real artifact and on-demand parity tests.
- [x] M3 operator engine/image adapter; reviewed inactive deployment configuration.
- [x] M4 real local protection/viewing; live endpoint acceptance remains M5.
- [ ] M5 cluster acceptance, fault/recovery cases and retention evidence.
- [ ] M6 independent final reviews, required gates and closeout.

- [x] (2026-11-10) Independent source correctness, QA and security reviews passed.
- [x] (2026-11-10) Reviewed inactive receiving configuration and runbook copied to open-wepp-org.

## Surprises & Discoveries


`wepppy/rq/project_rq.py:set_run_readonly_rq` does more than toggle a flag: it holds
`catalog_lifecycle_guard`, refreshes pending scopes and creates a browse manifest.
Failure can restore the prior read-only flag. Finalization must account for that
ordering and not advertise successful protection after a failed transition.

The cluster's execution-plane runbook describes fourteen general worker slots;
this is repository documentation, not verified current capacity. Never replace
or drain active workers merely to obtain the slice's worker.

Elevation query is a genuine zero-write HTTP DEM consumer, not an RQ task. Its
existing endpoint lacks project authorization; v1 explicitly admits public source
and public projects only. READONLY is not a complete mutation fence. Archive
restore currently deletes the admission directory, requiring preserved protection
through interrupted restore. No kubectl executable exists in this local shell.

## Decision Log


2026-11-10 20:18 UTC, user/author: target open-wepp-org for the working slice, with
shared RQ science and an independent engine. Fresh canonical projects avoid copied
workspaces; no incremental rebuilds or imported results. Keep frontend minimal;
accept report compatibility errors without compatibility machinery. Do not enable
Bootstrap. Determinism and cross-build comparison are deferred.

2026-11-10 20:18 UTC, author planning recommendation: first use `fetch_dem_rq`
with one provider and bounded extent, one dedicated worker if no child-wait exists,
and a real derived DEM viewer operation. These reduce the number of simultaneous
unknowns. M1 fixes exact fields/paths and records any evidence-based adjustment.

2026-11-10, execution: canonical bounded protocol is
`docs/schemas/declarative-dem-v1-contract.md`. Independent correctness/security
reviews approved after stable lifecycle publication, interrupted-restore protection
and separate finalizer authority were specified. Implement before deployment
handoff; do not claim M5 cluster evidence from local tests.

## Outcomes & Retrospective


Contract checkpoint and local on-demand science/readback are complete. Shared
observations, bounded adapter, engine and protection are implemented with focused
tests; broader integration, deployment preparation and final reviews are active.
No cluster deployment or cluster runtime validation has run. This package cannot close until M5 demonstrates the
real user workflow and M6 closes reviews. Planning completion is not implementation
completion.

## Context and Orientation


Work in `/home/workdir/wepppy` (also commonly `/workdir/wepppy`). Deployment source
is `/workdir/open-wepp-org`. Read each repository's root and nearest `AGENTS.md`
before edits. Do not switch branches or overwrite unrelated dirty files.

The authoritative direction is `docs/schemas/declarative-model-build-spec.md`,
currently proposed with implementation conformance pending. The architecture
findings are in `docs/reviews/declarative-model-build-spec-review.md`. Actual image
verification remains unproven. RQ is the existing Redis-backed job queue; NoDb
owns project controller persistence. Git checkpoints record selected boundary
state, not immutable consumed inputs throughout execution.

`wepppy/rq/project_rq.py:fetch_dem_rq` resolves map values, persists them through
Ron and calls `ron.fetch_dem()`. `wepppy/nodb/core/ron.py` owns that acquisition.
Reuse the scientific path without cloning its implementation. Also inspect
`wepppy/rq/project_rq.py:set_run_readonly_rq`, browse manifest writers,
`wepppy/query_engine/catalog_refresh.py`, frontend project rendering, and the
actual DEM-consuming view/task chosen in M1. Locate relevant handlers with `rg`;
record exact touched functions before edits instead of inventing route names.

Read the NoDb persistence, RQ response, batch-task boundary, query-engine catalog
refresh, artifact observability and generated-artifact validation contracts.
Ordinary on-demand projects without new metadata retain their behavior. Read-only
allows explicitly contracted derived writes, not arbitrary model mutation.

Deployment entry points are documented in open-wepp-org's
`docs/operations/weppcloud-canary.md`, `docs/operations/weppcloud-rq-execution-plane.md`
and `docs/operations/flux-gitops.md`; configuration is under
`clusters/openwepp/apps/weppcloud/`. Its roadmap, AGENTS_RIGHTS and live-change
rules apply. Re-read current versions before proposing deployment commands.
Do not create an ad hoc parallel deployment workflow or expose a new public API.

## Plan of Work


### M1 — Establish the bounded contract and acceptance fixture


Inspect the DEM writer, a real DEM-consuming interactive view/derived task and
project creation. Select one existing supported provider and a small valid extent;
record exact source/extent, generated paths, parser and user-facing URL/task in
`artifacts/validation_matrix.md`. Choose a fixture that needs no watershed model
execution. If none exists, document the concrete gap before expanding science.
Capture baseline on-demand artifact contents, status and latency.

Prepare the exact additive metadata and task record contract: model/build IDs,
project association, task/node/attempt IDs, source selection/retrieval time,
effective parameters, actual image evidence, input/output fingerprints, outcome
and checkpoint linkage. Define valid absent/empty/legacy state and malformed
requests separately. Select visible provenance paths, keep bulky rasters out of
Git, and inventory protected versus derived writes. Preserve archive visibility.

In the deployment repository inspect the actual image publication/GitOps path,
mounts, identity, free capacity and obtainable runtime evidence. Specify how the
engine binds each attempt to a worker/container and checks selected versus actual
image/platform. No claimed verification may rely only on job arguments or queue
names. Record missing evidence as an unresolved gate rather than a fabricated ID.

Complete `artifacts/20261110_contract_decision.md`, amend every affected canonical
contract with conformance pending (including bounded read-only/catalog semantics),
and obtain two independent read-only reviews. Use existing accepted user policy;
record recommended defaults explicitly. Follow the contract-first standard's
standalone ancestor commit requirement before UI/NoDb/RQ implementation. If commit
or new policy approval is needed, prepare the concrete checkpoint first. No
approval or review is implied by this scaffold.

### M2 — Add shared observations without changing science


Implement small shared provenance helpers at an owned location selected in M1,
not in the independent engine. Around `fetch_dem_rq`, capture resolved map/source
values at the actual acquisition boundary, timestamps, actual image observation,
output identities and explicit evidence quality. Avoid later NoDb reloads being
misrepresented as consumed parameters. Keep ordinary task signatures/defaults.
On-demand diagnostic publication failures remain visible without changing existing
scientific success; mandatory handoff failures retain their contracts.

Use project-local durable records and a serialized exact-path Git publisher.
Records contain unique attempt identity so a commit can be found after a crash;
a record cannot contain its own enclosing commit hash. No Bootstrap enablement
or remote Git transport is added. Test real file writes, Git commits, NoDb reads,
redaction and interruption. Verify existing on-demand DEM and Bootstrap behavior.
Measure overhead; do not invent global performance thresholds.

### M3 — Wire the independent operator engine and image adapter


Keep orchestration separate from science. Put the engine entry point and minimal
schema module in an owned location selected and documented in M1; use a private
operator invocation, not a new always-on HTTP service. The image-local adapter
validates its single schema/protocol and dispatches existing shared tasks.
Define commands for validate, submit, status and cancel, documenting exact invocation
and machine-readable result fields once the module path is chosen.

Admit only approved exact image digests and supported resource selections. Reject
invalid definitions before project/task side effects. Allocate a normal project
per accepted build; a submission ID resolves duplicate submission to that project.
Bind execution claims to attempts so duplicate delivery does not rerun uncertain
science. Persist build state in the project rather than Redis alone.

Prepare version-controlled deployment changes in open-wepp-org for the bounded
engine execution and one build-specific queue/worker. Preserve ordinary queues,
credentials, namespace and mount boundaries; never replace active fleet workers.
A single worker is allowed only after proving no selected task blocks on queued
children. The engine waits outside that worker. Keep descendant routing explicit
if any child exists. Update the RQ dependency catalog and inspect live job trees.

### M4 — Finalize protection and prove actual subsequent tasking


Use the shared read-only contract to protect scientific configuration, input/output
artifacts and historical records. After writers settle, finalize catalog/browse
requirements and read-only state, then publish completion last. Define durable
handling for failure between these steps. Retain failed/canceled projects and
protect them after old writers stop without converting failure into success.

Implement additive declarative awareness in the existing frontend/views. Enforce
protection in direct API and task execution paths, including jobs queued before
finalization; hiding controls alone is insufficient. Prohibit Bootstrap operations.
Do not temporarily clear read-only for reports. Permit only the selected derived
view task's explicit output/cache/operational writes under the shared contract.
Amend catalog behavior only when actual viewing requires it.

Run the real selected viewer task after finalization and read its generated result.
Fingerprint protected artifacts before/after, proving they did not change. A later
viewer failure belongs to its own attempt; historical build success remains.
Incompatible optional reports may fail visibly; no compatibility layer is added.

### M5 — Validate on open-wepp-org and exercise bounded failures


Prepare rendered manifests, image identity, target context, impact, rollback and
commands using current deployment runbooks. Observe all live-change authorization
requirements; the current task prepares source and an inactive handoff only. Do not apply broad manifests or
alter production Compose. Retain exact revisions and workload identifiers, not
secrets. Validate the whole path under actual identities, groups, mounts and umask.

Exercise a successful build and genuine later derived task; mismatch/unavailable
image evidence; invalid source/definition; duplicate submission/delivery; a failed
DEM acquisition; checkpoint publication failure; cancellation/worker loss; and
read-only finalization failure. Use disposable slice projects and bounded fault
injection, not shared filesystem outages or termination of unrelated workers.
Stop new scientific dispatch on failure. Explicit rerun creates a fresh project
after previous writers stop; do not add automatic stage replay.

Read real raster semantics and exact downstream consumption. Verify normal
browse/download plus archive/restore membership and record bytes. Git internals
need not be public, but ordinary visible provenance records must be accessible
under existing project authorization. Retain costs and all failed evidence.

### M6 — Review and close the working slice


Obtain independent correctness/UX, QA and dedicated security review using the
package artifacts. Close all medium/high findings and validate the final revision.
Update canonical contracts, operator instructions and open-wepp-org roadmap/runbook
as applicable. Run required broad/scoped gates and distinguish unrelated baseline
failures from regressions with evidence. If cluster acceptance is unavailable,
report locally validated only and leave the package open. Update tracker, plan,
root board and closure notes; preserve history rather than claiming future scope.

## Concrete Steps


From `/home/workdir/wepppy`, begin with read-only discovery:

    git status --short
    rg -n 'def fetch_dem_rq|def set_run_readonly_rq' wepppy/rq/project_rq.py
    rg -n 'fetch_dem|readonly' wepppy/nodb/core/ron.py
    rg -n 'readonly|dem' wepppy/microservices/rq_engine wepppy/weppcloud/routes

Record exact focused test paths in M1, then use `wctl run-pytest tests/<selected>`
for those real files. Before code closeout run:

    wctl check-rq-graph
    wctl run-pytest tests --maxfail=1
    wctl run-npm lint
    wctl run-npm test

Frontend commands apply when frontend files change; stub/API changes additionally
require `wctl run-stubtest <changed-module>` and `wctl check-test-stubs`. Expected
results are passing relevant tests and no unexplained graph drift, not invented
pass counts. Regenerate a legitimately changed RQ graph with the repository tool
and inspect the live tree through `wepppy/rq/job_info.py` or the dashboard.

From `/workdir/open-wepp-org`, after verifying target access and reading the runbook,
`scripts/weppcloud-rq-info.sh` is the documented read-only queue summary. Never
print Redis URLs or credential files. Record the exact render/apply/reconcile and
rollback commands in M3 before deployment; they depend on current GitOps state
and are deliberately not guessed in this scaffold. M3 must also replace the engine
invocation description with executable commands before claiming it runnable.

For documentation use:

    wctl doc-lint --path docs/work-packages/20261110_declarative_dem_vertical_slice
    wctl doc-lint --path docs/schemas/declarative-model-build-spec.md

## Validation and Acceptance


A valid operator definition must produce a fresh canonical project with a readable
DEM matching its requested extent/source semantics, a task-associated Git record,
verified actual worker identity and truthful completion state. The normal frontend
identifies it as declarative/read-only. A real derived task consumes that DEM and
publishes a viewable result while protected artifact fingerprints remain unchanged.

An invalid definition creates no scientific job or project mutation. An image
mismatch never yields verified success. A missing checkpoint retains outputs but
blocks completion. Duplicate admission does not create two builds; uncertain task
execution does not trigger automatic replay. Failed/canceled work remains distinct
from success. Optional absent legacy provenance does not break ordinary projects.

Check valid empty/new state and hostile paths separately. Test protected mutation
through UI, direct API and queued tasks; permit valid viewing through all supported
paths. Existing source access and feature permissions remain effective. Record
all results in the validation matrix, with exact revision and live evidence.

## Idempotence and Recovery


Repeat read-only discovery/lint freely. Reuse submission IDs only to observe the
same build; deliberate reruns allocate new projects. Reconcile already-published
commits by unique attempt identity, but never forge missing historic checkpoints.
For interruption stop old writers before a fresh build. Keep failed projects/logs
for diagnosis. No deletion or rollback of unrelated project trees is permitted.

Rollback disables only the new operator admission path and scoped worker resources,
then restores previous deployment configuration through existing GitOps procedures
after active jobs are accounted for. Preserve completed/read-only projects and
provenance. Do not clear read-only or run a schema downgrade to hide incompatibility.
Document exact resource names and previous digests before any live change.

## Artifacts and Notes


Keep sanitized source/extent, project/job/attempt IDs, chosen/observed image digests,
worker/container binding, raster readbacks, Git IDs, protected-file comparisons,
viewer results, archive checks, costs and fault outcomes in package artifacts.
Large rasters remain in normal project storage; evidence links identify their
location and fingerprint. Template review documents are not completed reviews.

## Interfaces and Dependencies


The initial definition must identify schema version, approved image, resource
selection, map extent and requested DEM product. Admission yields a durable build
ID and normal project ID. The image-local adapter maps that definition to the
existing `fetch_dem_rq` signature; it does not accept arbitrary Python callables.
Attempt records associate logical operation, RQ identity, observed runtime,
effective inputs, outputs and disposition. Completion references selected attempts
and required evidence after read-only protection. Fix concrete names/serialization
in M1's canonical contract before implementing these interfaces.

Use existing owned RQ/NoDb/Git/project and deployment mechanisms. Any new library
requires the repository dependency precedent/evaluation gates. Do not add a
provenance database, general policy service or immutable storage layer. Shared
image observations may be extensible to all project RQ tasks, but this slice must
not claim complete task enrollment or a production Compose rollout.

Revision note, 2026-11-10 20:18 UTC: created the planning scaffold to turn accepted
architecture into a bounded, verifiable end-to-end slice; implementation remains
pending the contract checkpoint and the appropriate execution task.

## Final local review update — 2026-11-10

All independent source high/medium findings are resolved. The real local RQ
fixture matrix covers successful publication/finalization/viewing, duplicate
submission, source/initialization/checkpoint/grid/finalizer failures and queued
cancellation. A real manifest fault preserves READONLY and truthfully fails.
Actual provider acquisition retains identical baseline DEM bytes and explicit
unknown registry identity. M5 cannot be inferred from these local observations.

The receiving package/runbook is inactive in open-wepp-org. Parent image
transformation means the fleet and dedicated image must match. Existing consumers
must receive mutation guards before admission, and retained declarations prohibit
rollback to a pre-guard image. This deployment sequencing is documented in
`artifacts/deployment_handoff.md`. Full Python and final focused/docs gates are
tracked in the validation ledger before local handoff.

## Local handoff complete — 2026-11-10

Source implementation is `185429547`; receiving preparation is `5c98b96`. Local
checks/reviews are complete, with the confirmed unrelated baseline template
assertion explicitly retained in the ledger. The initial broad process lost its
terminal result at an environment reset; retained continuations and final focused
runs supply the documented coverage, not a fabricated full-suite pass. A legacy
Ron test double gained required identity fields; independent QA approved the test
correction. No production code changed after the reviewed implementation commit.

M2–M4 and local M6 preparation are complete. M5 and final closeout remain open.
Next action is the authorized receiving canary using the inactive runbook, actual
published manifest and live preflight. Do not close this package before target
runtime/artifact/viewing and failure-recovery acceptance.
