# Deployment handoff — declarative DEM

**Execution complete — 2026-11-11 UTC.** Roger authorized this handoff and its
additive table migrations. Corrected source `f02e78cc0` is deployed; real success,
HTTP/archive and owned fault gates passed; temporary workers are removed and
ordinary services/Flux are healthy. See [receiving acceptance](receiving_acceptance.md)
and [final test disposition](final_full_suite.txt). Preserve all historical
attempts; this record is not an instruction to replay them.

The original pre-deployment handoff below is retained as historical provenance
and is superseded by those execution records.


The implementation is ready for a bounded open-wepp-org canary handoff. No image has
been published or deployed by this package. M5 and package closure remain pending
real cluster acceptance. Current local gates and any limitations are recorded in
`validation_matrix.md`; independent correctness, QA and security reviews are peers
in this directory.

## Receiving work

Receiving repository: `/workdir/open-wepp-org`.

- `docs/work-packages/20261110-declarative-dem-canary/package.md`
- `docs/work-packages/20261110-declarative-dem-canary/tracker.md`
- `docs/operations/declarative-dem-canary.md`
- `scripts/render-declarative-dem.py`
- `templates/declarative-dem-pod.json`

These are inactive preparation. The renderer creates a reviewable fixed-fixture
definition, approvals, Pod, ConfigMap and Kustomization. No generated resource is
included in live Flux desired state until an authorized receiving deployment.
The runbook contains exact render/engine/reconcile commands, target, capacity
preflight, acceptance gates and containment. Source implementation candidate is `185429547`; receiving preparation commit is
`5c98b96`. The selected child-manifest digest must be recorded before activation.

## Required deployment sequence

1. Publish the reviewed source with the existing WEPPcloud image workflow, retain
   the linux/amd64 child manifest and source evidence, and record a compatible
   recovery image. No synthetic test digest is an approval.
2. On the management node verify `admin@openwepp`, namespace `weppcloud`, actual
   node capacity and idle affected workers. The local development environment has
   no kubectl; these are unexecuted receiving gates.
3. Roll the candidate through the existing app pin/GitOps procedure. All web,
   rq-engine, worker, Bootstrap and request-plane mutation consumers must have the
   guards before admission. The app image transform and dedicated Pod must resolve
   to the same selected digest. Do not stop active jobs to free a slot.
4. Admit one bounded public build on the dedicated tokenless worker. Retain real
   Pod/Node/container/image/RQ evidence and inspect DEM content, task checkpoints,
   protection and truthful completion.
5. Exercise ordinary page viewing/elevation HTTP query, browse/download and
   archive/restore with protected fingerprints unchanged. Exercise owned failure,
   cancellation and worker-loss cases, then close both trackers after reviews.

## Recovery and limits

The engine never replays uncertain science. Status does not create or modify a
project. Cancel targets only the bound job; completion stays false for failed or
canceled science. Missing worker/cleanup evidence remains incomplete. Stop new
admissions and settle owned writers before pruning only the dedicated overlay.
Preserve READONLY, history and science artifacts. Do not serve retained declarative
projects with an old image lacking these guards.

Source tests use real Redis, RQ work horses, NoDb, local Git, actual read-only
manifest generation and raster readback. Their source raster and Pod identity are
fixtures. Separate ordinary acquisition used the real configured provider. Neither
is proof of cluster scheduling, runtime imageID format, browser authorization,
running-job cancellation or production-equivalent mounts/groups/umask.

The selected source/project is public because the existing elevation service lacks
private-project authorization. No new scientific formula/default is introduced.
Large ordinary DEM observation memory/cost remains an explicit follow-up: the
962-cell timing does not bound an 8192-by-8192 DEM. Full raster readback uses the
existing rasterio/numpy dependencies; no replacement science or new dependency.

## Final source gate

102 focused tests and 1069 frontend tests pass. Retained broad continuations have
6401 unique passes/241 skips and one reproduced preexisting TTL-help template
assertion; the ledger records the session-reset limitation rather than claiming
one clean full-suite run. Correctness, QA and security have no open high/medium
source findings. Stub hygiene, graph, lint and inactive-render checks pass.
The subsequent test-double/evidence commit changes no production code.
