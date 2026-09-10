# Deliver the production M1 upload and run workflow


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
Maintain Progress, Surprises & Discoveries, Decision Log and Outcomes &
Retrospective. The owner has requested execution. Runtime work follows the
accepted/reviewed/committed contract checkpoint.

## Purpose / Big Picture


A land manager or hydrologist can prepare an eligible WEPPcloud project, upload
a dNBR map, see upload readiness, run the Staley M1 model and access completed
model files. State survives reload, and failed replacements preserve prior work.
The owner plans to test a 10 m project. Reports/charts/dashboard are deferred;
this increment provides the minimal control necessary for upload and execution.

## Progress


- [x] (2026-09-10 07:23 UTC) Read backend/runtime precedents and scaffold contracts.
- [x] Draft simple UI labels/layout, workflow boundaries and state/decision matrices.
- [x] (2026-09-10) Incorporate owner revisions for live preflight, dNBR terminology, no date fields, Auto scale, filename/format guidance and unavailable NOAA.
- [x] (2026-09-10) Record distribution-based Auto and uploaded-map summary table; draft ADR-0063.
- [x] Evaluate/freeze distribution-v1 criteria with three real products, normalized equivalents and analytical cases.
- [x] Produce six-state static preview; record owner execution authorization and concrete contract.
- [ ] Two independent contract reviews; disposition; standalone ancestor commit.
- [ ] Implement NoDb state, owner prerequisites and freshness with tests.
- [ ] Implement authorized upload/publication and RQ model execution.
- [ ] Implement approved minimal control and reload/file-access behavior.
- [ ] Real end-to-end validation and independent correctness/security/UI reviews.
- [ ] Target preflight/install approval as needed; operator 10 m smoke handoff.

## Surprises & Discoveries


The completed local libraries assume trusted immutable paths and explicit hashes;
those assumptions are not an upload security boundary or live freshness authority.
The new adapter must establish source association, stage safe files and preserve
attempt ownership. WBT exists as a validated local build, not a guaranteed worker
installation. RUSLE's source organization is reusable, but its many parameter
controls and implementation-heavy prose are not the UI template for this feature.

## Decision Log


2026-09-10 07:23 UTC: owner requests production M1 NoDb/prerequisite/freshness,
dNBR upload/publication and RQ execution, explicitly deferring reports. Owner
requires simple, logical, organized UI using land-manager/hydrologist terminology.
Draft only: three-part preparation/upload/run flow, fixed M1, one design-source
choice, no advanced model knobs. Detailed defaults/copy need explicit review.

2026-09-10 owner revision: Required project data must use realtime preflight;
label dNBR “differenced Normalized Burn Ratio”; remove image-date entry; default
the scale select to Auto with presets and conditional Custom numeric fields;
persist accepted filename, explain formats/datatypes and disable unavailable NOAA.
Rationale: familiar terminology and less map-preparation friction. Updated owner direction: Auto
attempts scale identification from the valid-value distribution, with metadata as
evidence and scale selection on ambiguity. Show upload details and applied scale
in a wc-control__panel-summary table. Evaluate criteria under ADR-0063. Resolve retry/evidence details at checkpoint, preserving the
backend's explicit scale API and scientific provenance.

## Outcomes & Retrospective


Scaffold only. No runtime, tests, contract-approval artifact, review signoff or
deployment exists. A later scaffold commit is not the required approved checkpoint.
Owner UI revisions are synchronized across the domain/UI contracts and package;
numerical distribution criteria and staged scale-correction retry remain proposed details.

## Context and Orientation


Repository `/workdir/wepppy` (also `/home/workdir/wepppy`), baseline `304572530`.
Preserve unrelated dirty code-quality reports and current branch. Read root,
`wepppy/nodb/AGENTS.md`, module AGENTS, `wepppy/weppcloud/AGENTS.md`, controller
JS AGENTS, rq-engine AGENTS, tests AGENTS and smoke-test guidance before touching
those areas. Canonical proposals are module `docs/production_m1.md` and
`docs/ui-docs/contracts/postfire-debris-flow-control-contract.md`.
For live readiness also read `services/preflight2/AGENTS.md`,
`docs/ui-docs/control-ui-styling/preflight_behavior.md`, `wepppy/nodb/redis_prep.py`
and `wepppy/weppcloud/static/js/preflight.js`. Existing Redis keyspace notifications
feed the Go preflight service, browser checklist and `preflight:update` event.
Extend that flow additively for this control rather than creating another socket.

Applicable shared contracts: `docs/standards/contract-first-change-standard.md`,
`docs/schemas/nodb-persistence-concurrency-contract.md`,
`docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`,
`docs/schemas/rq-response-contract.md`, `docs/schemas/weppcloud-csrf-contract.md`,
`docs/ui-docs/controller-contract.md`, and feature-registry specification/YAML.
Resolve project-config/effective-locale authority from its current contracts;
registry labels/config names cannot define CONUS. Read those owners before
freezing locale behavior. UI availability and server enforcement must agree.

Existing module libraries: `dnbr.normalize_dnbr` creates a new normalized
artifact, `integration.build_m1_predictors` creates T/F/S and coverage, and
`results.build_m1_results` consumes completed predictor/Climate snapshots for
wet-event/design/inverse outputs. Verify actual module/signature via its current
contract before wiring. All paths/hashes/identity arguments are explicit. WBT
StaleySlopeSbs computes Horn on raw DEM and preserves uncertainty. Use accepted
scientific policies/ADRs 0054–0059 and 0062; no estimator changes in this package.

Project scope is existing positive routed bound.tif cells and resolved outlet,
not new catchments. Built WEPP soils, SBS, named RUSLE Nomograph K, accepted
dNBR and Climate event parquet are prerequisites for run. Only grid/domain and
eligibility/access are needed for upload. M1 K readiness does not require full
RUSLE completion. NOAA is needed only for NOAA design choice. Partial dNBR can
supply F; unknown T or incomplete K can yield diagnostic results without point
probabilities. WBT decoder preparation remains owned by existing local adapter.

Inspect RUSLE facade/control/routes and current upload helpers for ownership,
status/auth/queue patterns, not wholesale copying of UI prose or options. Planned
paths: module `postfire_debris_flow.py`/`__init__.py`, a focused production
orchestration collaborator if needed, `wepppy/rq/postfire_debris_flow_rq.py`,
`wepppy/microservices/rq_engine/postfire_debris_flow_routes.py`,
`wepppy/weppcloud/controllers_js/postfire_debris_flow.js`, and
`wepppy/weppcloud/templates/controls/postfire_debris_flow_pure.htm`.
Do not implement a report template. Register feature/control through existing
feature-registry and run-context mechanisms, preserving older debris_flow.

## Plan of Work


Milestone 1 makes the UI and runtime contract concrete. Read the UI contract
end-to-end. Produce a static non-runtime preview with real typography/layout for
empty, ready, partial, running, failed and stale states; plain HTML artifact or
other reviewable rendering is sufficient. No implementation templates/controllers
may be edited yet. Do not add status cards, tabs, model parameters, confirmation
modals, report tables or duplicated actions beyond the draft. Resolve owner
feedback in the current UI contract, not only in chat or a screenshot.

Finalize exact NoDb keys/version, immutable directory layout, upload/run attempt
IDs, route methods/paths, multipart and JSON fields, responses/error codes,
auth/CSRF, streaming file/request limits, VRT companion mapping, scientific and
operational states, idempotency, cleanup/reconciliation and all dependency edges.
Complete package state/request matrix and canonical expected-error copy. Proposed
state fields cover active_dnbr_id, upload_attempt, run_attempt, rainfall_source,
last_successful_run_id, dependency_snapshot and freshness; these are proposals,
not frozen executable schema. Proposed mutations are upload-dnbr and run-m1
under existing run-scoped task routing, with read-only state hydration. Freeze
actual naming against router conventions instead of adding parallel API patterns.

Record compatibility/regression plan: new optional NoDb and artifact subtree,
no old debris_flow state/output migration, upstream source mutation or implicit
build. Prepare `artifacts/<date>_contract_decision.md` with starting revision,
all contract deltas/rationale, security impact, discrepancy classification, state
matrix and observable evidence. Obtain explicit operator approval including UI
copy/layout/defaults. Two independent read-only contract reviewers must disposition
findings. Commit approved checkpoint and current canonical amendments as a
standalone ancestor; record its hash before any runtime edits. No inherited
commit authority for ordinary prior packages substitutes for this checkpoint.

Milestone 2 implements state/readiness. Thin NoDb facade and focused collaborators
follow existing lock/cache conventions. Read GET preserves absent optional state;
first authorized write creates it. Run readiness examines current WBT/domain,
Soils inventory, SBS and K provenance, normalized dNBR grid/assessment and Climate
snapshot. Resolve effective CONUS, legacy us and boundary policy before adding
gates; the owner's 10 m smoke test does not authorize restricting all M1 to 10 m.
Readiness returns stable machine states plus UI-friendly required actions.
Wire those states into preflight producer updates and invalidations, with initial
hydration and reconnect reconciliation. Inspect affected upstream mutation owners
and the preflight service checklist before freezing payload keys. Cover changes
to K, soils, SBS, watershed, climate, accepted dNBR and NOAA without page reload.
Do not mistake completed tasks for fresh artifacts. Keep decoding/full hashing
outside preflight heartbeat handling; worker source checks remain authoritative.

Create per-attempt immutable storage. Stage original uploads with generated
names and safe ownership; record original filename separately. Long decoding,
hashing and numerical work runs outside locks. Finalize through short refreshed
allowlisted mutation with attempt/version/source checks. Persist active pointers
only to completed verified artifacts; stale completions cannot overwrite newer
attempts. Document orphan/restart recovery without deleting unrelated files or
prior successful results. Unit preference changes are presentation-only.

Milestone 3 implements transport/workers. Reuse existing upload/auth/CSRF and
RQ response contracts. Stream bound input before decoder invocation, enforce
format/source allowlist and reject path/network escapes. VRT companions come
only from explicitly staged files. Submit a normalization job with metadata and
identity; resolve Auto to explicit scale/offset using robust distribution evidence
and metadata checks. Evaluate deterministic sampling, quantiles, outliers and
selection criteria against fixtures under ADR-0063 before freezing the algorithm.
Unqualified identity metadata, dtype alone or a single extreme is insufficient. An ambiguous
candidate remains unpublished and can be retried with a selected preset/custom
scale without retransferring the file. Freeze bounded candidate retention, expiry,
authorization and attempt checks; no extra confirmation button. No image-date
inputs or missing-date gate. Preserve source metadata when actually available.
The job calls accepted backend, checks current grid/attempt and publishes
accepted dNBR. Upload transfer success alone is not ready. Replacement failure
preserves previous accepted source and run output. New publication marks derived
results stale. Test normalization and publication with actual source files.

Run submission validates current owner readiness, snapshots selected options
and coalesces matching duplicates. Proposed single worker snapshots/copies or
otherwise pins immutable required inputs and composes predictors then rainfall
results, recording job phases through existing status facilities. Recheck source
association/identity before finalizing active result. Use current local manifest
schemas and explicit provenance, never arbitrary paths supplied by browser.
Timeout/retry and partial writes follow frozen contract. Unsupported rainfall
scenarios and missing point predictors can produce completed diagnostic output;
operational failures cannot be disguised as scientific unavailability.

Dependency invalidation must cover source deletion/rebuild, DEM/grid/outlet/SBS/
Soils/K/dNBR/climate changes, selected rainfall source and model/tool parameters.
Preserve older results as previous, not current. Reuse valid predictor artifacts
for rainfall-only changes if the frozen freshness contract proves independence.
A queued/running result whose inputs change must be superseded, not promoted.
Test concurrent upload/model finalizers directly at persistence boundaries.

Milestone 4 implements only the approved control. Write controller tests first
per shared convention, then template/controller/feature registration and hydrated
state. Exact labels and actions come from the UI contract. Use standard controls
and one shared status area/log. Required data links lead to existing controls;
no implicit prerequisite build from this control. Source selector affects design
storms only; project events remain project events. Completed output gets fixed
protected file access using existing run-file listing/download contracts, not a
new archiver/report system. Verify private output modes work across web/worker.

Milestone 5 validates and prepares target handoff. Run actual browser upload →
queued normalization → accepted dNBR → run job → completed artifact pointers →
reload/status/file access in dev with production-equivalent identities/groups/
mounts/umask/orchestration. Include invalid/partial overlap, encoding presets,
failed replacement, first use, read-only, duplicates, stale dependencies, mid-job
mutation, worker retry/failure and previous-output preservation. Verify input
hashes/assessment, T/F/S and all result files, not only a green status string.
No report is needed to inspect JSON/parquet through authorized file access.

Update RQ dependency catalog and graph; manually inspect a real job tree with
job_info/dashboard. Verify the worker actually has StaleySlopeSbs and matching
binding/API; a local Rust release build is not worker readiness. Independent
correctness, security and UI behavior reviews must close all medium/high issues.
Run required suites after final changes; keep evidence tied to exact revisions.

Prepare installation/deployment preflight and rollback through canonical
scripts/deploy-production.sh and nearest operator docs. Identify the actual
user test target; do not deploy without target authority. The user's later 10 m
project is an operator acceptance case, not a reason to fabricate a run URL or
block earlier dev evidence. Record local implemented, target installed, and
operator tested as distinct outcomes. If target/project unavailable, hand off
completed local work plus exact remaining smoke checklist without claiming
production deployment or operator acceptance. Do not close unmet release gates.

## Concrete Steps


At repo root inspect git status/revision and preserve unrelated quality reports.
Read canonical contracts and create approved ancestor before runtime changes.
Proposed tests: module facade/workflow, rq-engine routes, controller JS and a
browser smoke test under existing canonical test conventions. During iteration
use focused wctl run-pytest paths. Required final gates:

    wctl run-pytest tests --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl check-test-stubs
    wctl check-rq-graph
    wctl doc-lint --path docs/work-packages/20260910_staley_m1_production
    wctl doc-lint --path wepppy/nodb/mods/postfire_debris_flow
    wctl doc-lint --path docs/ui-docs/contracts/postfire-debris-flow-control-contract.md

Use module stubtest when public API changes and rebuild controller bundles via
existing controller-JS tooling. If graph drift is reported, regenerate using
`python tools/check_rq_dependency_graph.py --write`, inspect changes and validate
live job trees. Record exact browser smoke command after environment discovery.
Do not run runtime suites for this documentation scaffold alone.

## Validation and Acceptance


An eligible new project reaches upload and execution without manual NoDb creation
or extra technical forms. Required missing data is understandable and actionable.
The actual model runs and produces downloadable completed files. Reload preserves
state, stale inputs are visible, and failed attempts do not replace accepted
artifacts. No old debris_flow data changes. Unit changes leave scientific values
identical. All states in the finalized matrix have direct evidence, including
malformed requests and valid optional-state initialization. UI review verifies
logical order, labels, keyboard interaction, focus/errors and no unapproved
controls. No charts/report renderer are added.

## Idempotence and Recovery


Each attempt writes new private artifacts. Duplicate submits attach to current
matching jobs. Superseded workers cannot publish. Failed writes retain diagnosable
incomplete attempts under a documented cleanup policy; success pointers are
unchanged. Retry with fresh attempts and source snapshot checks. Rollback must
preserve accepted artifacts and old module state; never disable auth/CSRF or
relax decoder checks to make a smoke test pass.

## Artifacts and Notes


Retain UI preview/state screenshots, contract decision and reviews/ancestor,
state/request and invalidation matrices, compatibility plan, real job trees,
source/generated hashes, browser/worker identity evidence, validation and final
independent reviews. Keep tracker and current contracts synchronized. Closed
scientific packages are reference evidence and must remain unchanged.

## Interfaces and Dependencies


New PostfireDebrisFlow facade with explicit state version, current dNBR/run
pointers and readiness method; exact signatures freeze at checkpoint. Existing
local numerical libraries are dependencies, not new implementations. RQ workers
receive authorized run context and server-generated attempt identity, not raw
browser filesystem paths. Use existing feature registry, Pure UI macros,
NoDb/RQ/CSRF contracts and protected file-serving paths. No external dependency,
report service or generic workflow framework is needed.

Revision note: initial production scaffold prioritizes exact user-facing layout
and labels, first-use/reload/failure semantics and real upload/run validation;
report and dashboard implementation are explicitly deferred.

Revision note (2026-09-10): incorporated owner-requested preflight updates,
dNBR terminology, date-field removal, Auto select, persistent filename/format
guidance and disabled unavailable NOAA. Validate live upstream changes and
reconnects in browser acceptance; run `wctl run-preflight-tests` and, when service
wiring changes, `wctl run-preflight-tests -tags=integration ./internal/server`.
Test distribution-based detection, metadata conflicts, ambiguity correction and candidate access/expiry before
publishing uploads. These changes reduce preparation friction without guessing
the numerical encoding or exposing internal workflow machinery.

Revision note (2026-09-10, subsequent owner feedback): Auto must attempt value-
distribution identification rather than requiring explicit metadata. Add the
uploaded-map wc-control__panel-summary table specified in the UI contract; it is
within upload scope, not the deferred model report. ADR-0063 records the accepted
direction and pending numerical evaluation. No runtime implementation yet.

Revision note: execution authorized by owner; checkpoint review/commit precedes
runtime edits. ADR-0063 and distribution fixture evidence now record numerical
criteria. No deployment authority is inferred.
