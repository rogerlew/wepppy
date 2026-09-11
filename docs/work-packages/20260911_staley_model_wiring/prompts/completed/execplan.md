# Execute Staley M1/M3 UI and RQ wiring

## Purpose


Users select M1 or M3 in the existing Post-fire debris flow control, see only
relevant required inputs and submit to the appropriate RQ worker task. M1 uses
its current scientific pipeline. M3 reaches a real task with an explicit
integration_pending failure until the separately deferred scientific integration.
Do not close roadmap stage 6 or claim M3 probabilities. No production deployment.

## Progress


- [x] Record owner UI/DEM/masking/mod decisions and inspect SSURGO rules.
- [x] Create canonical selection amendment and ADR-0066.
- [x] Complete independent contract reviews and disposition (both accepted).
- [x] Commit standalone contract ancestor aa30e637e with explicit owner authority.
- [x] Implement model UI/state/admission/freshness and dedicated M3 RQ task.
- [x] Validate focused/npm/Go checks and real development browser/job tree.
- [x] Finish full Python suite: 8,468 passed, 103 skipped; final evidence recorded.
- [x] Complete correctness/security reviews and archive this wiring plan.

## Context and contracts


Work at /home/workdir/wepppy on master; preserve unrelated quality reports.
Read nearest AGENTS before edits. Current authority is module specification.md,
docs/model_selection.md, docs/production_m1.md and the shared UI contract at
docs/ui-docs/contracts/postfire-debris-flow-control-contract.md. Shared contracts:
docs/ui-docs/controller-contract.md; docs/schemas/rq-response-contract.md;
weppcloud-csrf-contract.md and nodb-persistence-concurrency-contract.md in that
schemas directory. Artifact observability and contract-first standards apply.

UI template is wepppy/weppcloud/templates/controls/postfire_debris_flow_pure.htm;
controller is wepppy/weppcloud/controllers_js/postfire_debris_flow.js. Backend
sources/get_state/execute_model are in the module production.py. Facade state
is in postfire_debris_flow.py. Dispatch is in microservices/rq_engine/
postfire_debris_flow_routes.py and rq/postfire_debris_flow_rq.py under wepppy.
Preflight consumers and source fingerprints must use model identity consistently.

## Milestone 1: accepted checkpoint


Amend canonical contracts before code, preserving implementation-pending status.
Obtain independent correctness and security reviews and close medium/high findings.
Record commit authority and create a standalone checkpoint ancestor. Never treat
this plan or a historical package as substitute canonical authority.

## Milestone 2: UI and compatibility


Use existing control header/table/radio/fieldset/file display patterns. M1 is
default. Hide complete dNBR upload/summary group for M3, but preserve artifacts and
job diagnostics. M1 prerequisites omit independent Soils; M3 omits K/dNBR and
requires effective Ron.cellsize 10 and Ron.dem_db ned13/2022. Retain shared
watershed/SBS/climate and NOAA availability. Keep automatic mod dependencies.
Model and rainfall selectors serialize explicitly, with request generation checks
to discard stale model readiness responses. Persist model selection separately
from attempt/result identity without reclassifying past outputs. Show result model.
Coverage metadata/link is additive when supplied later; never fabricate it.

## Milestone 3: route and worker wiring


Add /postfire-debris-flow/run with explicit model and frequency_source; retain
/run-m1 pinned to M1. Use existing strict bounded JSON/auth/CSRF/readonly/locale
contracts. Preserve queued receipt before enqueue and worker ownership. Matching
active request includes model; different active model returns canonical busy.
Wire M3 to run_m3_rq(runid, identity), not run_m1_rq. Until composition exists,
persist running then failed integration_pending with a useful public message and
visible error log; return a genuinely failed RQ job, no success publication.
Do not change worker signature or leak paths/secrets in public preflight errors.
Reconciliation validates correct function name and immutable attempt association.

Snapshots exclude unrelated model sources. Legacy state without model is M1;
legacy results stay visible and can become stale after a changed engine/source
contract. Do not reinterpret or rewrite old predictor manifests. Model selection
alone is not permission to alter a running attempt. Worker finalization checks its
own model's captured dependencies, not unrelated selected-model inputs.

## Milestone 4: validation and handoff


Write meaningful regressions for model switching/reload, out-of-order preflight,
legacy/empty/populated state, model-specific dependencies, duplicate/different
submissions, worker reconciliation and M3 failure persistence. Exercise actual
NoDb locks/filesystem plus existing archive tests, not only mocked orchestration.
Run wctl run-pytest for affected module/microservice/RQ tests, wctl run-npm lint
and wctl run-npm test, then wctl run-pytest tests --maxfail=1. Run wctl
check-rq-graph and regenerate canonical catalog if needed. Scoped doc lint too.

Use the existing development authenticated browser and service identities on
addicted-reservist, preserving accepted outputs. Demonstrate both selections,
conditional fields, reload, M3 enqueue/job failure and correct job-tree association.
No live soil rebuild or new source upload is required. Keep credentials out of
logs. Record exact evidence and complete independent correctness/security reviews.
Update tracker/roadmap; archive only the completed wiring increment. Stage 6
must still list full M3 composition and valid-support numerical work as pending.

## Surprises & Discoveries


SSURGO Horizon.valid addresses WEPP property readiness, not interval topology;
its constructor runs unrelated property estimation. The existing offline M3
helper already validates intervals. Evaluate reuse there before adding rules.
Production M1 currently includes independent built Soils in admission/freshness;
hiding its row alone would leave the request blocked.

Singleton refresh can replace an earlier controller reference; test fixtures
now read durable state or reacquire before direct writes. Real overlapping
preference/worker/publication mutations passed against Redis. Initial enabled
selectors could persist template rainfall before state restoration; disable
until live. Recorder click events share run admission with preference saves;
explicit pre-admission job_active alone receives bounded, visible retries.
Headless WebGL rendering slowed browser automation; collapse the existing Map
control and focus the postfire section while retaining all normal recording.

## Decision Log


2026-09-11 UTC: owner chose 10 m ned13/2022, requested existing SSURGO rule
assessment, scalar valid-support estimates and mask download, retained automatic
POLARIS/RUSLE enablement, and required M3 to reach its RQ task now. Reports and
full scientific integration remain subsequent work. No probability-bound UI.

2026-09-11 UTC: both reviewers accepted the bounded selection-only busy retry
as conformance to the approved serialized-save behavior. Record this mechanism
and its recurrence-triggered reassessment in the canonical selection contract;
never exempt recording, weaken shared admission, or retry model jobs.

## Outcomes & Retrospective


Implementation, independent source reviews and live validation complete.
Checkpoint ancestor: aa30e637e. Both dedicated task identities are recorded in
artifacts/live_job_trees.json. M1 completed; M3 reports integration_pending,
retaining its error and prior M1 results. Browser readback verifies saved NOAA,
conditional inputs, retry with recording enabled, download200 and live preflight.
Full Python 8,468 passed, 103 skipped; npm 872 and lint passed. All reviewer
conditions are satisfied, and this wiring plan is archived. M3 scientific
composition, valid-support aggregation/mask and reports remain outside this
completed wiring increment; do not close roadmap stage6.


Preflight scope: amend module preflight.py and Go checklist projection with the
canonical production_m1.md “Preflight completion task” policy. 🌋 reflects the
latest accepted result's own model/frequency; selection alone never invalidates
it. Validate both relevant and unrelated model dependency changes with Python
and `wctl run-preflight-tests` Go tests, plus actual development stream readback.
