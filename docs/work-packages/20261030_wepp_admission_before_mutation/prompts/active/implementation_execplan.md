# Establish WEPP admission before applying inputs


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
Maintain Progress, Surprises & Discoveries, Decision Log and Outcomes & Retrospective.

## Purpose / Big Picture


A rejected execution request must leave its proposed model inputs unapplied so
already-admitted work cannot consume them. Configuration-only batch/base saves
must continue to work. The proof is a changed request rejected with HTTP 409,
unchanged persisted input values and a real prepared input still containing the
accepted request's value.

## Progress


- [x] (2026-10-30 22:00 UTC) Record master/revision and unrelated dirty work; inspect handler, payload, leases, replay and worker reloads.
- [x] (2026-10-30 22:00 UTC) Identify five confirmed static consumers and prepare canonical amendment and state matrix.
- [x] (2026-10-30 22:04 UTC) Two independent checkpoint reviews pass; low error-mapping wording finding corrected and dispositioned.
- [ ] Obtain commit authority and create standalone checkpoint ancestor; record SHA in tracker.
- [ ] Write failing regression, implement bounded ordering correction, then prove accepted/rejected persistence and prepared-input behavior.
- [ ] Run focused/full gates and independent correctness/QA reviews; update affected docs and final evidence.

## Surprises & Discoveries


Both bootstrap WEPP no-prep routes call the same payload writer before their
submission helper. They are confirmed peers even though they do not regenerate
prepared inputs. HTTP middleware holds a lifecycle lease but does not enforce
active-work admission, so it does not close the persisted-input defect.

## Decision Log


2026-10-30 UTC, Codex: classify WAM-01 as a normative amendment. Current response
contract promises no duplicate enqueue, not nonmutation on execution rejection.
The operator explicitly approves the correction but withholds commit authority;
implementation must wait for the reviewed checkpoint ancestor. Preserve existing
no-prep metadata saves after admission and prepared-file immutability.

## Outcomes & Retrospective


Diagnosis and proposed contract only. No implementation, runtime reproduction of
mixed results, prepared-artifact validation, deployment or production repair yet.
The missing commit authority is a real sequencing gate, not a request to approve
the already-authorized correction again.

## Context and Orientation


Work in `/home/workdir/wepppy` on `master`, starting at
`29716c1bd9a24dacf1cb45e05a11b2aa44a5378e`. Preserve all preexisting dirty paths in
`artifacts/initial-status.txt`, particularly Roads work and generated usersum index.
The original instructions are retained at `artifacts/operator-prompt.md`.

`wepppy/microservices/rq_engine/wepp_routes.py::_handle_run_wepp_request` serves
run-wepp, run-wepp-watershed and prep-wepp-watershed. It currently calls
`wepp_run_payload.py::apply_wepp_run_payload` before `rq_submission_lock` and
`ensure_no_active_wepp_job`. The payload helper saves NoDb controller files.
`bootstrap_routes.py` has two equivalent callers, run-wepp-npprep and
run-wepp-watershed-no-prep, using `_enqueue_no_prep_job`. That helper also serves
SWAT; preserve SWAT behavior. Workers in `wepppy/rq/wepp_rq_stage_prep.py` load
controllers later, so a rejected request can change their inputs.

A submission lease is the existing renewable ownership lock implemented in
`wepppy/rq/submission_recovery.py`; its lifecycle lock also excludes other run
mutations. Deferred reconciliation safely cancels associated waiting prior jobs;
active queued/started/scheduled descendants remain conflicts, even after the
parent dispatcher finishes. Read current contracts named in the decision artifact
and nearest AGENTS before code edits.

## Plan of Work and Milestones


Milestone 1: prepare and independently review the contract checkpoint. Current
canonical text belongs in `docs/schemas/wepp-run-input-contract.md` WAM-01 with
response/webhook cross-links. Record operator authorization, starting revision,
classification, compatibility and security impact in the decision artifact.
Disposition both reviews. Request authority only after the checkpoint is concrete;
commit only approved checkpoint paths and record its SHA. Do not edit production
or regression code before that ancestor exists. Do not stage unrelated changes.

Milestone 2: add failing behavior tests in the existing WEPP and bootstrap route
modules, plus direct real persistence/coordination coverage. Preserve existing
fixtures' stub isolation. Test changed values and durable reload, not source order.
Then separate configuration-only detection from payload mutation in the shared
handler. Keep its existing payload error mappings through a small local helper if
needed; apply directly for batch/base, and after reconciliation/active admission
inside the existing lease for execution. Keep finally-based ownership-safe release.
In bootstrap, pass the parsed payload into the existing submission helper and
apply after its WEPP admission checks; retain optional empty-payload behavior and
all no-prep error mappings, without regeneration or changes to SWAT callers.

Before moving work, inspect `apply_wepp_run_payload` side paths including
revegetation and SWAT metadata for duration/lock inversion. Existing lease renewal
is every 30 seconds to 120 seconds. Keep lifecycle → family → controller lock
ordering, checkpoint before/after apply and before receipt/enqueue writes. Do not
hold locks for model execution or remote computation. A released precheck is not
a fix. Late failures do not acquire new rollback guarantees.

Milestone 3: demonstrate controlled A/B interleaving using actual Redis leases
and file lifecycle fence on unique disposable identities. A accepted, B rejected,
A's state remains durable. Exercise active descendants and fail-closed association.
Use real NoDb controllers, parser and preparation with a representative disposable
fixture: set an accepted soil conductivity or slope override, reject a changed
value, prepare and parse the exact parameter in `wepp/runs/`. Retain hashes,
semantic values, environment identity and revision. For no-prep, assert prepared
file bytes do not change. Do not run production jobs or an expensive full model.
Record unavailable environment boundaries explicitly.

Milestone 4: run required checks, update operator/developer/user documentation
proportionately and obtain independent correctness and QA reviews. Retain existing
artifact browse/download/archive/restore evidence for representative paths; no new
artifact layout is planned. Keep package open while any required evidence is
missing. Deployment and production recovery are excluded.

## Concrete Steps and Validation


From `/home/workdir/wepppy`, run focused routes first:

    wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_bootstrap_routes.py --maxfail=1

Discover and run existing payload, reconciliation and submission lease suites
using `rg --files tests | rg 'wepp|submission|recovery|lifecycle'`. Add targeted
new tests to appropriate existing modules. Required acceptance groups are all
five active/busy rejection paths, controlled concurrent submissions and active
child, successful receipt identity/persistence, batch and normalized base variants,
webhook new/replay/conflict, validation/persistence/enqueue failure release, and
deferred recovery plus lifecycle exclusion. Cover sparse/false/zero/legacy payloads.
Assert persisted fields, no new queue item, unchanged active receipt/hint and
completion metadata, while permitting legitimate prior-state reconciliation.

After code changes run:

    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master

Run `wctl doc-lint --path <file>` for changed docs and preview `uk2us` diffs.
No frontend edits are planned. Queue sites/edges should stay unchanged; if changed,
update catalog, run `wctl check-rq-graph`, and inspect a disposable real job tree.
Record actual results; skipped or blocked tests are not passes.

## Idempotence and Recovery


Use unique disposable test run/Redis identities and remove only owned fixtures.
Do not install dependencies or start containers automatically. Missing services
are validation blockers. Restore only this package's patch if rollback is needed;
never reset the user's working tree. No branch switching, production submissions,
deployment or broad Redis deletion.

## Artifacts and Notes


`artifacts/assessment.md` holds the bounded consumer/state matrix, error policy
and evidence chain. `artifacts/20261030_contract_decision.md` records normative
delta and authority. `tracker.md` holds ancestor SHA and executed results.
Pre-implementation baseline tests alone do not prove the correction.

## Interfaces and Dependencies


Reuse `apply_wepp_run_payload`, `rq_submission_lock`, `SubmissionLease.checkpoint`,
`reconcile_deferred_wepp_jobs`, `ensure_no_active_wepp_job`, current webhook
Submission and existing response helpers. No dependency or payload schema changes.
NoDb durable controller semantics remain authoritative for readback.

Revision note (2026-10-30 UTC): created after tracing shared and bootstrap peers;
implementation awaits the required reviewed ancestor commit.
