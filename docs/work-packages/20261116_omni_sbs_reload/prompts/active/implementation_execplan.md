# Restore Omni SBS map reload and repeat submission


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
Maintain Progress, Surprises & Discoveries, Decision Log, and Outcomes &
Retrospective along with the package tracker at each handoff. Contract-first execution was authorized on 2026-11-16; the milestones below
are now active.

## Purpose / Big Picture


An Omni SBS scenario is a model scenario using an uploaded soil burn severity
raster. Users should reopen it, see its current filename, and submit again
without uploading the same map. A replacement remains optional. Completion
requires both the visible UI and the actual scenario input to agree.

## Progress


- [x] (2026-11-16 19:05 UTC) Inspect source and scaffold bounded package.
- [x] (2026-11-16 19:05 UTC) Record contract-first and scoped-test instruction.
- [ ] Capture browser reproduction and exact canonical contract amendments.
- [x] (2026-11-16 UTC) Author shared staging and Omni contracts; reconcile freshness/upload rules.
- [ ] Complete accepted contract checkpoint and standalone ancestor commit.
- [ ] Add failing targeted tests and implement the contracted fix.
- [ ] Rebuild assets; verify browser, filesystem, and generated output behavior.
- [ ] Complete independent reviews and documentation; disposition limitations.

## Surprises & Discoveries


The UI already renders a conditional `Current file:` help paragraph from saved
`sbs_file_path`, but serialization drops that path. A filename display alone
cannot repair submission. The normal reader returns persisted definitions that
include that field; the reported absence of the display needs runtime evidence.

Run admission resolves a raster from the current numeric row's temporary folder,
while the SBS copy lifecycle can unlink the source. The freshness contract
allows narrowly verified reuse of consumed inputs but still requires an input
when execution is necessary. This is a contract decision as well as a UI bug.

## Decision Log


On 2026-11-16 the user required contract-first implementation and scoped validation.
Do not run full repository pytest or full frontend suites. Scope additional tests
to affected consumers only. The initial turn delivered the scaffold; execution is now authorized.

Use the canonical `Current SBS map` display and keep saved associations separate
from browser Files. Preserve public keys and names where possible. The user subsequently directed simple resolution from `_limbo` or the corresponding
Omni scenario project. Use the saved upload first, otherwise the associated
scenario map, with existing validation. Missing historical receipts alone do not
require re-upload. Stage child input before a destructive rerun; preserve existing
freshness decisions about output reuse. No new store or legacy migration.

## Outcomes & Retrospective


Source-level diagnosis and a restartable implementation plan are complete.
No browser reproduction, contract acceptance, implementation, or runtime
validation has occurred. The key discovery is that the temporary-upload lifecycle
must be tested alongside the visible saved state.

## Context and Orientation


Work from `/home/workdir/wepppy`. Read the nearest AGENTS before editing each
subsystem, including `wepppy/weppcloud/controllers_js/AGENTS.md`,
`wepppy/microservices/rq_engine/AGENTS.md`, `wepppy/nodb/AGENTS.md`, and
`tests/AGENTS.md`. Read smoke-test instructions before authenticated browser work.
Preserve unrelated dirty files and do not create a branch.

`wepppy/weppcloud/controllers_js/omni.js` owns `load_scenarios_from_backend`,
`updateScenarioControls`, `createControlElement`, and `serializeScenarios`.
It reads `api/omni/get_scenarios` and submits multipart data to rq-engine
`run-omni`. `wepppy/weppcloud/routes/nodb_api/omni_bp.py::get_scenarios` returns
`Omni.scenarios`. `wepppy/nodb/mods/omni/omni_input_parser.py::parse_scenarios`
stores SBS definitions with `type` and `sbs_file_path`.

`wepppy/microservices/rq_engine/omni_routes.py::_prevalidate_omni_sbs_inputs`
validates fresh uploads or locates one existing file in `omni/_limbo/{idx:02d}`.
A claimed path currently acts as a presence flag, not a stable association.
`wepppy/nodb/mods/omni/omni_mode_build_services.py` copies the selected map into
the scenario child's disturbed directory through `omni_sbs_freshness.py`.
That helper records content identity and can delete the consumed source.
`omni_run_orchestration_service.py` owns reuse versus rerun decisions.

The canonical presentation reference is
`wepppy/weppcloud/templates/controls/disturbed_sbs_pure.htm`, using
`ui.text_display`, label `Current SBS map`, a code-formatted filename, and an
empty-state message. `controllers_js/disturbed.js::updateCurrentFilename`
updates that display with text-safe DOM operations. Reuse its presentation,
not its global singleton state for per-scenario maps.

## Plan of Work


### Milestone 1: Reproduction and accepted contract

Inspect a representative project's saved response and current browser bundle.
Capture upload, run, reload, and failed submission without a replacement.
Separate missing UI presentation from dropped request state and consumed-source
admission. Enumerate never-used, empty, populated/pending, consumed-with-receipt,
legacy-without-receipt, missing, ambiguous, and hostile states. Also cover archive
restore, forked paths, failed/in-progress execution, and multiple scenarios.

Prepare `artifacts/20261116_contract_decision.md`. Starting revision is
`65fa0c0bd008b16157a82191a766a0bdb9453173`; record the actual implementation
base again at execution time. Inventory and reconcile the canonical contracts
listed in package.md. First create `docs/schemas/user-file-staging-contract.md`
for the shared lifecycle: project/input association, validation before acceptance,
replacement preserving prior input on failure, consumption and safe deletion,
explicit resolution locations, and cleanup ownership. Define consumer opt-in;
Omni is the first consumer, not proof that other uploads already conform. Do not
introduce a generalized storage implementation or migrate other consumers.

Create `docs/ui-docs/contracts/omni-sbs-control-contract.md` for the exact
hydration/display/replacement/request/error contract and Omni's staging details:
`omni/_limbo` layout, scenario association, lookup order, and preservation before
child reset. Cross-link the shared staging contract and existing upload/freshness
contracts. Keep generic lifecycle rules out of the SBS freshness specification;
keep raster content identity and output-reuse rules in that specification. Amend
freshness and upload contracts if resolving consumed inputs changes their rules.
Do not promote unreviewed proposed behavior as implemented.

Choose how saved identity resolves independently of row order. Prefer an
existing persisted association with run-contained validation; introduce a new
identifier only if retained evidence shows existing fields cannot meet acceptance.
Implement the user-directed resolution rule: use the associated saved upload in
`_limbo` when present, otherwise the corresponding scenario project's saved SBS
map. Validate the available file using existing helpers, including for older
projects without receipts. Stage it through existing machinery before resetting
the child for a rerun. If neither location has a usable associated map, request
replacement. Do not add persistent storage, migrations, or a new receipt scheme.
Retain old state on failed validation. Document the
compatibility and rollback plan before any data/schema changes.

Record the operator's accepted exact semantics. Obtain two independent read-only
contract reviews, disposition findings, and commit the checkpoint and canonical
amendments as an ancestor before code changes. Obtain commit authority if it
has not been given. Do not seek duplicate approval for already accepted behavior;
the checkpoint records the approved two-location rule and reconciles it with
the existing freshness contract, rather than reopening that user decision.

### Milestone 2: Focused regressions and bounded implementation

Add SBS tests to `wepppy/weppcloud/controllers_js/__tests__/omni.test.js` that
load a saved definition, show its basename, and serialize it with no selected
File. Cover fresh replacement, invalid replacement, multiple rows, row removal,
blank rows, type switching, and rehydration. Assert multipart indexes agree with
the submitted definitions. Render actual template conventions where changed.

Implement per-row saved state and canonical display in `omni.js` and its paired
template if needed. Keep accepted state separate from pending replacement. Do
not preserve references across unrelated scenario types by accident.

Add direct admission/filesystem tests in
`tests/microservices/test_rq_engine_omni_routes.py`; use actual raster files and
real containment/validation helpers at changed boundaries. Implement only the
accepted saved-reference resolution in `omni_routes.py`. If the chosen lifecycle
requires NoDb or copy changes, add targeted tests in
`tests/nodb/mods/test_omni_sbs_freshness.py` and the existing parser/mode/orchestration
service test modules. Preserve content validation and stale-input detection.
Assess direct, queued, and batch consumers of each changed helper; repair confirmed
shared failures without redesigning unrelated workflows.

### Milestone 3: Scoped validation and observable acceptance

Rebuild the controller bundle. Run the targeted commands below and record exact
results. Exercise the browser against a disposable representative project using
the generated bundle and normal run endpoints. Verify an unchanged repeat submit
and separately force a dependency change that requires execution, under the
accepted contract. Confirm the correct map survives the full path.

Capture normal-reader persisted definitions, actual request, accepted source,
child raster semantic metadata/content digest, generated landuse/soil and
`wepp/runs` contents, execution outputs, and fresh report readback. A successful
job or filename display alone is insufficient. Record revision, run, runtime
identity/groups/mounts/configuration; use production-equivalent boundaries.
If the environment or data is unavailable, retain the blocker and narrow the
completion claim instead of substituting mocks.

### Milestone 4: Review and handoff

Produce independent correctness/UX and security review artifacts using
`docs/prompt_templates/correctness_review_template.md` and
`docs/prompt_templates/security_review_template.md`. Close medium/high findings.
Update affected user help, Omni developer documentation, operator recovery notes,
and canonical contracts in the final change set. Update tracker and root project
board. Promote all durable rules outside this package before closure. Deployment
and affected-run repair require separate evidence and authorization.

## Concrete Steps


From `/home/workdir/wepppy`, use scoped commands during implementation:

    wctl run-npm test -- omni.test.js --runInBand
    wctl run-pytest tests/microservices/test_rq_engine_omni_routes.py --maxfail=1
    wctl run-pytest tests/weppcloud/routes/test_omni_bp.py tests/weppcloud/routes/test_omni_bp_routes.py --maxfail=1
    wctl run-pytest tests/nodb/mods/test_omni_sbs_freshness.py --maxfail=1
    python3 wepppy/weppcloud/controllers_js/build_controllers_js.py

Run parser, mode-build, orchestration, or RQ test modules only when those paths
are changed or implicated. Determine the canonical wrapper's targeted ESLint
invocation from `static-src/package.json` and wctl help before running it; do not
invoke a script that silently lints the entire frontend. Documentation checks:

    wctl doc-lint --path docs/work-packages/20261116_omni_sbs_reload

Use the docs-maintainer spelling preview for changed prose. Record actual
commands and pass/fail counts; do not invent expected counts. New regression
cases should fail against the old implementation and pass against the candidate.

## Validation and Acceptance


A user can load a saved SBS scenario, read `Current SBS map`, submit with an empty
file chooser, reload again, and see the same accepted association. Repeat after
successful execution consumes the original temporary file. Replace a map and
confirm the replacement's bytes reach the intended scenario. Reject invalid or
unauthorized references without losing the old accepted state. Test two maps and
row deletion so basenames and indexes cannot silently select the wrong input.

Show an explicit missing-map message only when the accepted policy cannot safely
resolve an input. Verify legacy behavior, same-name changed content, and fresh
execution under changed dependencies. Keep non-SBS behavior compatible. Review
both valid-state success and hostile-state containment. No completion claim may
exceed retained browser/artifact evidence.

## Idempotence and Recovery


Use disposable projects for destructive scenario reruns. Back up fixture state
before lifecycle tests and record cleanup. Never delete user uploads or repair
production runs as part of validation. Repeated read/submit cycles must preserve
map identity. Rollback restores the previous code/bundle; if storage behavior
changes, document old-reader compatibility before implementation. Do not claim
code rollback restores overwritten scenario outputs.

## Artifacts and Notes


Store reproduction, scoped test results, browser screenshots/request summaries,
and compact semantic artifact comparisons under this package's `artifacts/`.
Exclude credentials, session tokens, and large copied project trees. Initial
source diagnosis is recorded in package.md; no runtime artifact exists yet.

## Interfaces and Dependencies


Reuse `WCHttp`, existing multipart uploads, NoDb persistence/locking, raster
admission helpers, and SBS freshness receipts. Keep `sbs_file_path` and public
scenario names compatible unless an approved contract explicitly requires an
additive change. A client reference is a selection claim; server-owned association,
containment, and current content validation determine whether it can be used.
No new external dependency is permitted by this plan.

Revision note (2026-11-16 19:05 UTC): Initial scaffold, including the user's explicit
contract-first and scoped-validation requirements; implementation not started.

Revision note (2026-11-16 UTC): User clarified that existing maps may be in
`_limbo` or the Omni scenario project and requested simplicity. Recorded one
resolution rule for old/new projects; removed the open storage/legacy-policy fork.

Revision note (2026-11-16 UTC): User approved an independent user-file staging
contract within this package. Added it to the contract milestone and scoped
lifecycle acceptance; Omni remains the sole implementation consumer in scope.
