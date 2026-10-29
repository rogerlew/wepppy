# Implement project developer mode with one-way activation


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Maintain Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective along with the package tracker. The operator has now instructed execution of this work package, authorizing implementation, required checkpoint commit and validation. Production deployment remains out of scope.

## Purpose / Big Picture


A developer can enable experimental anisotropy inputs without an off toggle on one project from the PowerUser panel. Other callers with ordinary project operation access can then use those inputs without a Dev role. Projects remain normal by default, and clones retain their source policy. Success is visible in a project indicator and in actual prepared soil files, not just saved settings.

## Progress


- [x] (2026-10-29 00:51 UTC) Record operator-approved behavior and scaffold implementation.
- [x] (2026-10-29 UTC) Obtain and disposition independent contract/package reviews; C2/C3 design fixes confirmed.
- [x] (2026-10-29 01:06 UTC) Operator approved incoming archive/source state replacing prior mode, including true-to-normal transitions.
- [x] (2026-10-29 UTC) Both reviewers confirmed lifecycle clarification; all design findings closed.
- [ ] Record reviewed contract ancestor commit before runtime edits.
- [ ] Implement Ron lifecycle and bounded activation UI/API.
- [ ] Propagate project policy through Python and rebuilt native preparation.
- [ ] Validate cloning, archive/restore, generated inputs and real execution.
- [ ] Finish docs, broad checks and independent runtime reviews.

## Surprises & Discoveries


Current upper/lower maxima are duplicated in the numeric-field template, `wepppy/nodb/core/soil_anisotropy.py` and sibling wepppyo3 `wepp_interchange/src/soil_anisotropy.rs`. Direct saved-state edits cannot bypass preparation validation. The PowerUser panel currently admits PowerUser/Admin/Root but not Dev-only accounts; simply broadening its outer gate could expose unrelated controls.

## Decision Log


2026-10-29 UTC, operator/Codex: use permanent Ron boolean, exact Dev activation, no additional role check for anisotropy submission, and clone inheritance. This avoids reset/clamping semantics and user-dependent background validation. Retain all soil behavior except explicit-override maxima. No runtime edits in the scaffolding task.

## Outcomes & Retrospective


Design and implementation sequence prepared. Runtime conformance, generated artifacts, native compatibility and deployment are not yet validated. Review dispositions and evidence will update this section; this scaffold alone cannot close the package.

Independent correctness/security reviews are complete. Mode/value consistency during cloning/archive creation and immediate UI refresh were added and confirmed. The operator explicitly permits archive restore and failed-fork recovery to replace mode with incoming state, including normal mode. No preservation or rejection mechanism is required. Both reviewers confirmed this clarification; all design findings are closed and no operator decision remains open.

## Context and Orientation


Ron is the project-wide NoDb controller stored in `ron.nodb`. NoDb serializes controllers under Redis locks with refreshed state and atomic file replacement; follow `docs/schemas/nodb-persistence-concurrency-contract.md`, not a direct JSON edit. `Wepp` owns saved anisotropy values. `soil_anisotropy.py` validates submissions and effective preparation settings. `WeppSoilUtil.modify_anisotropy` calls a Rust function through wepppyo3 and updates parsed horizons before the existing writer emits `wepp/runs/p*.sol`.

Canonical behavior is in `docs/schemas/project-developer-mode-contract.md` (DM-01), `docs/schemas/soil-anisotropy-contract.md` (SA-01), and amended ADR-0088. Read the applicable-contract matrix in `artifacts/20261029_contract_decision.md` relative to this package. Read nearest AGENTS for NoDb, WEPPcloud, controllers, rq-engine if touched, tests, and the sibling native repository. Do not create/switch branches or touch unrelated active packages.

## Plan of Work


### Milestone 1: Accept the checkpoint and inventory state consumers


Complete the two independent read-only reviews and primary dispositions, including reviewer confirmation of medium/high fixes. DM-01 fixes `POST /runs/<runid>/<config>/tasks/enable_developer_mode`, JSON `{}`, existing CSRF header, and HTTP 200 `{"Content":{"developer_mode":true}}`; malformed payloads are 400 and authorization/readonly denials are 403. Inventory panel entry buttons, clone/fork variants and archive restore. Apply the approved lifecycle exception: incoming archive/source state wins even when it clears mode; do not add downgrade rejection or sticky destination state. Commit the checkpoint and canonical docs alone as an ancestor with appropriate commit authority, and record its SHA in tracker.md. Current base is `cebb4b4283e408fd270126811f4dbbd1a8dfd8e2`; verify ancestry if the working tree has advanced. This milestone changes no implementation.

### Milestone 2: Persist and expose activation


Add `Ron.developer_mode: bool` and an enable-only mutation method to `wepppy/nodb/core/ron.py` and its stub. Missing state is false; malformed stored state fails explicitly; enable is idempotent under the existing lock/refresh contract. A read must not initialize/write missing state. Add a run-scoped POST in `wepppy/weppcloud/routes/nodb_api/project_bp.py` using existing response and exception conventions. Require exact Dev membership plus existing project/readonly/CSRF checks; accept no client-defined mode/limits or disable command. Do not add the mode to general WEPP inputs.

Write failing controller/route tests before UI behavior changes. Add the enable-only activation action to `wepppy/weppcloud/templates/controls/poweruser_panel.htm`, adjust panel launch availability for Dev-only users while preserving all unrelated action gates, and use the adjacent controller request/error conventions. Display mode to all authorized viewers outside the restricted panel. Failed requests show errors without claiming activation; reload handles lost responses. Verify actual HTTP/session/CSRF behavior and real NoDb persistence, not only mocks.

After activation succeeds, update mode status and remove maximum attributes from both current-page anisotropy fields while preserving unsaved values. Test that the user can immediately enter an elevated value without a mysterious browser validation failure. Do not widen eligibility or readonly behavior.

### Milestone 3: Wire anisotropy policy through native preparation


Resolve authoritative Ron mode for input validation and once per preparation operation. Keep existing omitted/blank behavior, pre-mutation validation, minimum 1, finite checks and MOFE/hourly eligibility. Carry that boolean through `wepppy/nodb/core/soil_anisotropy.py`, `wepp.py` and preparation collaborators into `WeppSoilUtil.modify_anisotropy` and sibling native `soil_anisotropy_values`. Extend native arguments additively with normal-mode default, preserving existing positional callers. Do not infer mode from payload, environment or caller roles. Revalidate saved active overrides and preserve existing one-read/one-write handling.

Render normal maximum attributes 100/10 and omit both maxima in developer mode; retain minimum and instability warning. Rebuild wepppyo3 following its local instructions and retain source/build hashes. An incompatible native module fails explicitly; no Python fallback. Verify normal boundary tests still pass and developer upper=101/lower=11 produce the expected horizons using the actual writer. No model equation or source-soil changes are permitted.

### Milestone 4: Prove lifecycle and end-to-end behavior


Exercise existing fork and archive code in `wepppy/rq/project_rq.py` and its helpers without changing queue topology. Clone a normal project and an activated project through real copy/rehydration, including an authorized non-Dev caller. Preserve mode, overrides and source hashes. Archive/restore includes `ron.nodb` and prepared inputs. Test restore over an activated project with archived true, false and missing mode; incoming state must win without a mode-based rejection. Concurrency tests must prove unrelated Ron writes cannot erase activation.

Add a real copy barrier test: copy source Ron=false, activate source, save elevated overrides, then finish copying Wepp state. Before clone publication, existing lifecycle serialization or post-copy mode reconciliation within the same lifecycle incarnation must prevent a normal-mode clone with experimental overrides. Also cover existing failed-fork destination replacement in `wepppy/microservices/rq_engine/fork_archive_routes.py`; its existing replacement behavior must use incoming source mode even when the destination was activated. Cover incoming true, false and missing state and ordinary failure/retry behavior; do not add preservation, rejection or a new Dev check. Lifecycle replacement invalidates earlier source observations through existing fencing; do not assume global monotonicity across restore.

Apply the same consistency requirement and controlled interleaving test to archive creation in `wepppy/rq/project_rq_archive.py`: capture Ron=false, activate/save elevated overrides, then capture Wepp. Do not publish an inconsistent archive. Restore the resulting archive through the actual reader and verify mode/value compatibility; mocked orchestration cannot substitute for the member-copy boundary.

On an isolated representative MOFE/hourly project, activate as Dev, submit elevated values as an otherwise-authorized non-Dev caller, prepare using the rebuilt native module and read `wepp/runs/p*.sol`. Compare depth classes and all unrelated fields against the normal baseline. Run fresh WEPP through the actual worker orchestration under production-equivalent identity, groups, mounts, umask and configuration. Retain exact consumed input and fresh outputs or numerical failure evidence and verify ordinary browse/download/report visibility. A passing job or persisted state alone is insufficient. Record preparation success separately if extreme values cause numerical failure; do not claim successful simulation without evidence.

### Milestone 5: Documentation and final reviews


Update the PowerUser user guide, model option docs, developer soil note and adjacent module docs with enable-only mode, clone inheritance, archive/fork replacement exceptions and paired-runtime requirements. Complete the correctness and security artifacts from repository templates with direct evidence. Close all medium/high findings and obtain independent confirmation. Update package/tracker/plan statuses without implying production deployment. Deployment requires a separately authorized canonical deployment workflow.

## Concrete Steps


Run commands from `/home/workdir/wepppy`; use canonical `wctl` containers for Python and frontend checks. Begin with `wctl run-pytest tests/nodb/test_soil_anisotropy.py tests/weppcloud/routes/test_project_bp.py tests/rq/test_project_rq_fork.py tests/rq/test_project_rq_archive.py`. Add focused tests for Ron lifecycle and the changed panel controller, and record their exact paths here. Inspect sibling `/home/workdir/wepppyo3` instructions for the native test/build command and record it before rebuilding rather than inventing a parallel build path.

For frontend changes run `wctl run-npm lint` and `wctl run-npm test`. Rebuild controller assets using `python3 wepppy/weppcloud/controllers_js/build_controllers_js.py` when that source directory changes. Run `wctl run-stubtest wepppy.nodb.core.ron`, relevant changed-module stub checks and `wctl check-test-stubs`. Before handoff run `wctl run-pytest tests --maxfail=1`, plus broad-exception and code-quality checks specified in root AGENTS. Run `wctl doc-lint --path <changed-doc>` for each changed Markdown file and preview `uk2us` diffs. If queue wiring unexpectedly changes, stop to assess scope and require catalog/graph/live-tree validation; it is not planned here.

## Validation and Acceptance


Default and legacy projects still reject upper 101 and lower 11 without mutating saved values. Dev can activate, but PowerUser/Admin/Root without Dev cannot. Dev-only users can reach the action without gaining unrelated controls; readonly and CSRF denials remain effective. Authorized non-Dev callers can submit those values after activation. Boolean/malformed/NaN/infinite/<1 values remain invalid. Missing/blank, inactive, populated and malformed state are distinct cases; role/input combinations do not replace that state matrix.

Acceptance includes idempotent activation after durable reload, actual clone/archive state inheritance and approved replacement and real generated upper/lower ratios with unrelated fields unchanged. Run the unmocked boundary checks for valid and hostile requests and the actual native writer. Record counts and failures, not predicted pass counts. Existing default prepared files must retain semantic parity. Numerical stability is outside the guarantee; visibility of an actual failure is within scope.

## Idempotence and Recovery


Repeated authorized enable requests succeed without resetting state; never expose a false setter. Existing archive restore and failed-fork recovery may clear mode by replacing project state; code-version rollback alone must not rewrite mode. Use disposable validation projects and retain source hashes. If a response is lost, read back mode before retry. If native/Python versions mismatch, stop preparation and restore a compatible pair. Older code may reject experimental saved values, so document rollback limitations and do not silently modify projects to make rollback pass. No bulk migration, production deployment or manual live-run editing belongs to this plan.

## Artifacts and Notes


Keep review findings/dispositions, exact commands/results, native build receipt, runtime identity, generated-input semantic comparison, clone/archive manifests and browser evidence in this package's artifacts directory. Do not store secrets. The current checkpoint and tracker distinguish documentation-only completion from runtime implementation, local validation, environment validation and deployment.

## Interfaces and Dependencies


Expose a boolean Ron getter and enable-only method; keep default native behavior normal via an optional boolean policy argument. Python owns authoritative project-state resolution, Rust owns finite/range checks and horizon selection. Use existing Flask/NoDb/RQ/Jinja/controller mechanisms and wepppyo3; no new dependency is authorized. Preserve SA-01 file formats, depth classification and original-source semantics.

Revision note: 2026-10-29 UTC — initial plan records operator-approved permanent project policy and required independent review, with implementation deliberately pending.

Revision note: 2026-10-29 01:06 UTC — operator chose existing archive/fork replacement semantics over preserving or blocking mode transitions, prioritizing simplicity and recovery flexibility. No off toggle is added; normal bounds resume after incoming normal state.
