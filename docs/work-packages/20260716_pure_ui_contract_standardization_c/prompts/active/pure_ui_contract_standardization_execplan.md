# Audit and standardize every Pure UI controller contract iteratively

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must remain current
as work proceeds.

Maintain this document in accordance with
`docs/prompt_templates/codex_exec_plans.md`. Keep
`docs/work-packages/20260716_pure_ui_contract_standardization_c/tracker.md` and
`artifacts/controller_audit_register.md` and
`artifacts/child_package_register.md` current at every stopping point. This plan
deliberately executes the initiative through bounded child work packages; it is
not permission to audit all controllers in one uncontrolled diff.

## Purpose / Big Picture

After this initiative, a maintainer can open one canonical contract for any Pure
UI domain controller and see the complete, current mapping from rendered fields
and user interactions through JavaScript serialization, route normalization,
NoDb/server persistence, RQ execution, errors, completion, and reload. A change
to a risk-bearing field or payload will have an executable test and a named doc
that must change with it.

The visible result is a complete contract set under `docs/ui-docs/contracts/`, a
verified controller register, and small closed work packages that contain their
own evidence and two independent reviews. The first pilot is WATAR/Ash because a
recent selector-name mismatch showed exactly how migration-era documentation and
field-id tests can miss a real payload regression.

## Progress

- [x] (2026-07-17 00:30 UTC) Created the umbrella package, tracker, initial
  register, reusable child-package protocol, and active ExecPlan.
- [x] (2026-07-17 00:30 UTC) Recorded explicit operator authorization for
  bounded subagent dispatch and mandatory dual independent review.
- [x] (2026-07-17 00:48 UTC) Completed two independent scaffold reviews,
  dispositioned one high, four medium, and six low findings, and received
  post-fix closure confirmation from both reviewers.
- [x] (2026-07-17) Authored the exact 70-unit register and populated the
  controller/module/surface ledger; both register reviews are dispositioned and
  independently confirmed closure-ready.
- [x] (2026-07-17) Reconciled the controller/component population, froze the
  70-unit register, and approved parent/exclusion decisions through dual review.
- [x] (2026-07-17) Recorded the operator's clarification that all included rows
  are contractual now; evidence maturity is a separate axis.
- [x] (2026-07-17) Scaffolded and dual-reviewed GOV-00A with no remaining
  high/medium findings; its ratification ExecPlan is ready for execution.
- [x] (2026-07-17) Began GOV-00A Milestone 1 by recording the operator's
  contract-first authority rule in root and UI/RQ/NoDb subsystem governance;
  both reviewers confirmed closure-ready with no remaining high/medium findings.
- [x] (2026-07-20 21:23 UTC) Operator authorized GOV-00A to register bounded
  cross-owner remediation REM-01 for the Omni mod-state defect.
- [x] (2026-07-20 21:40 UTC) Complete dual review for REM-01 with no unresolved
  high/medium findings.
- [x] (2026-07-20 22:42 UTC) Commit the two standalone REM-01 ancestors,
  execute only its registered defect boundary, complete dual final review, and
  close it after the 5,070-pass repository sweep.
- [ ] (2026-07-21 22:15 UTC) Ratify GOV-00A-M1B and REM-02's finite SURF-06
  TTL-deletion catalog presentation boundary before implementation.
- [ ] Ratify `docs/ui-docs/contracts/README.md` and its evidence levels.
- [ ] Execute and close the WATAR/Ash pilot child package.
- [ ] Use pilot findings to add a stable contract-coverage check.
- [ ] Execute all remaining registered packages through independent closeout.
- [ ] Consolidate stale links, run initiative-wide gates, complete both final
  reviews, and archive this ExecPlan.

## Surprises & Discoveries

- Observation: The existing documentation has two different jobs but does not
  separate them clearly. `docs/ui-docs/controller-contract.md` defines shared
  controller invariants, while
  `docs/ui-docs/control-ui-styling/control-inventory.md` contains migration-era
  field tables and explicitly lists future verification work.
  Evidence: the headings and `Next Actions` in those files.

- Observation: Controller-specific contract notes are embedded in
  `wepppy/weppcloud/controllers_js/AGENTS.md`, archived modernization plans, and
  domain READMEs. Some domain docs still link to a missing current
  `docs/ui-docs/ash-control-plan.md` even though the only matching plan is under
  an archived 2025 work package.
  Evidence: `rg -n 'ash-control-plan|controller-contract|control-inventory' docs
  wepppy`, excluding generated docs index output.

- Observation: Filename convention cannot define the full population. The
  bundle builder discovers nearly every JavaScript module, Pure templates include
  nested advanced options and modals, and standalone consoles can have separate
  render roots.
  Evidence: `build_controllers_js.py::_collect_controller_modules` and templates
  importing `controls/_pure_macros.html`.

- Observation: The run-page bootstrap currently registers 33 production
  controller entries, while `runs0_pure.htm` includes 26 main control panels and
  four supporting modal/panel templates. Batch Runner is a separate Pure
  surface. The population is therefore not one template per controller.
  Evidence:
  `wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2`,
  `runs0_pure.htm`, and Batch Runner route templates.

- Observation: Dedicated Jest suites exist for the 33 production entries, but
  many hand-author their DOM. The current Pure render test covers only a small
  subset of panels, so suite presence is not evidence that template macro output
  and controller serialization agree.
  Evidence: `wepppy/weppcloud/controllers_js/__tests__/`,
  `tests/weppcloud/routes/test_pure_controls_render.py`, and the WATAR Ash test
  fixture that already assumed the intended `name="ash_model"`.

- Observation: The migration inventory is explicitly dated 2025-10-22 and still
  contains future verification work and stale coverage gaps, despite its nearby
  AGENTS file calling it complete/source-of-truth.
  Evidence: `docs/ui-docs/control-ui-styling/control-inventory.md` and
  `docs/ui-docs/control-ui-styling/AGENTS.md`.

- Observation: The concrete WATAR failure boundary is rendered semantics, not
  visual appearance: a macro conversion can preserve an element id while
  changing the browser-submitted field name.
  Evidence: the WATAR incident's selector/payload regression and ash contract
  tests; the pilot must preserve this as an explicit `id != name` case.

- Observation: Direct macro-import discovery omitted state-changing templates
  that inherit Pure behavior transitively, including the security form family,
  user profile/session reset, and root user modification.
  Evidence: `templates/security/_layout.html`, `templates/user/profile.html`,
  and `templates/user/usermod.html`.

- Observation: The 56-module bundle inventory and 33-key run bootstrap are
  different populations. The bundle contains four standalone and 15 shared
  modules in addition to 37 run-support files.
  Evidence: deterministic output of `_collect_controller_modules()` and the
  primary-owner manifest in `artifacts/child_package_register.md`.

Add discoveries with exact paths, commands, or concise test output. Do not erase
historical observations when later evidence changes the design.

## Decision Log

- Decision: Add REM-01 as a bounded remediation unit without advancing the
  three borrowed domain owners.
  Rationale: GOV-00A now defines a reviewed path for finite cross-owner defects;
  the register must make its exception and exclusions explicit.
  Date/Author: 2026-07-20 / Operator direction, recorded by Codex.

- Decision: Use one umbrella ExecPlan to create and execute bounded child work
  packages rather than one monolithic controller audit.
  Rationale: The controller population crosses frontend, route, NoDb, and RQ
  ownership. Small packages keep evidence, security triage, review, and rollback
  meaningful while the umbrella register guarantees completeness.
  Date/Author: 2026-07-17 / Codex, from operator direction.

- Decision: Retain `docs/ui-docs/controller-contract.md` as the shared invariant
  contract and create per-domain contracts under `docs/ui-docs/contracts/`.
  Rationale: Duplicating singleton/bootstrap/StatusStream rules in every domain
  file would create another drift surface. Domain files instead own exact fields,
  payloads, persistence, and compatibility.
  Date/Author: 2026-07-17 / Codex.

- Decision: Contract status is evidence graded: `documented` is not `verified`.
  Rationale: Intended behavior and source inspection did not prevent the WATAR
  rendered-name mismatch. Verification requires rendered or runtime evidence and
  exact tests at a named revision.
  Date/Author: 2026-07-17 / Codex.

- Decision: Pilot on WATAR/Ash before enforcing register metadata in tooling.
  Rationale: The pilot contains enum labels/tokens, cached per-model values,
  multipart fields, RQ execution, NoDb persistence, and a known `id`/`name`
  regression. It will reveal which metadata can be maintained reliably.
  Date/Author: 2026-07-17 / Codex.

- Decision: Every umbrella and child package receives two independent reviews.
  Rationale: One reviewer traces semantic correctness; the other challenges
  regressions, compatibility, config coverage, and evidence. Independent roles
  reduce common-mode omission risk.
  Date/Author: 2026-07-17 / Codex, explicitly required by operator.

- Decision: Operator-authorized subagent dispatch is bounded and logged.
  Rationale: Parallel tracing and independent review are valuable, but shared-
  worktree edits and unrecorded authority create their own risk. The primary
  agent owns integration and may not infer deployment or production authority.
  Date/Author: 2026-07-17 / Codex, explicitly authorized by operator.

- Decision: Replace the ten broad audit waves with 70 stable execution units:
  the existing umbrella plus 69 future dated child directories.
  Rationale: Deterministic inventory found 33 run-page contracts plus shared and
  stateful non-run surfaces. Independent upload, queue, auth, and persistence
  boundaries need separate baselines, security triage, and review. Pre-splitting
  Map, Landuse, Climate, AgFields, WEPP/SWAT, shared bootstrap/shell foundations,
  and Batch avoids knowingly over-sized packages. Separate ERMiT export, RQ Info
  Details, and DEVAL loading units own their authenticated/privileged queue and
  artifact lifecycles. The register still parents true adjuncts that share one
  lifecycle.
  Date/Author: 2026-07-17 / Codex and two independent inventory reviewers.

- Decision: After GOV-00A cutover, `contract-obligations.json` is the sole
  machine obligation/status-summary authority; the audit register is its
  reviewed discovery projection, the child-package register owns execution,
  and the contracts README contains a registry-generated reader index.
  Rationale: Independently editable scope/evidence/status tables would drift.
  GOV-01 adds source/test/shared-consumer mappings without duplicating the
  obligation registry or publishing the reader index.
  Date/Author: 2026-07-17 / Codex, updated after operator direction and GOV-00A
  scaffold review.

- Decision: Enforce contract-first ancestry and subsequent same-change
  implementation maintenance with a source-to-contract manifest and a
  change-aware gate.
  Rationale: Existence, headings, and a historical verified revision cannot
  detect a later template/controller/route/NoDb/RQ change that leaves its
  contract stale. The gate must verify the accepted contract-decision ancestor,
  not merely co-occurring file changes. Shared producers must fan out to every
  mapped consumer.
  Date/Author: 2026-07-17 / Codex and independent governance reviewer.

- Decision: Treat all submitted, hydrated, persisted, enum/file, visibility-
  sensitive, and RQ-controlling values as material unless dual review approves
  an explicit exclusion.
  Rationale: An undefined "risk-bearing" subset is gameable and produces
  inconsistent verification across packages.
  Date/Author: 2026-07-17 / Codex and independent governance reviewer.

- Decision: Every included coverage row is `contractual / unverified` now;
  `candidate` is not a permitted inclusion status.
  Rationale: Candidate language can be interpreted as optional or
  non-contractual, defeating the register's purpose. Contractual obligation and
  implementation-conformance evidence must remain separate dimensions.
  Date/Author: 2026-07-17 / Operator direction, recorded by Codex.

- Decision: Add GOV-00A as the 71st execution unit and active ratification child.
  Rationale: Ratification has independent deliverables, validation, and dual
  review and should not be hidden inside the multi-year umbrella. It must finish
  before shared foundations and WATAR consume the schema.
  Date/Author: 2026-07-17 / Codex, from operator request to scaffold a
  ratification package.

- Decision: Canonical contracts are normative and must be amended before an
  intended UI or RQ behavior change is implemented.
  Rationale: Code and tests are conformance evidence, not a competing source of
  intent. Contract-first sequencing prevents defects or accidental behavior from
  being ratified after the fact. Restoring implementation to an unchanged
  contract requires regression evidence, not a normative contract rewrite.
  Date/Author: 2026-07-17 / Operator direction, recorded by Codex in GOV-00A.

## Outcomes & Retrospective

The scaffold is complete. Initial inventory and governance findings were
dispositioned, both reviewers confirmed closure-ready with no remaining high/
medium findings, and documentation checks passed. The initiative outcome is not
yet complete: no controller row may be described as verified until its child
package supplies the required evidence and reviews.

The pre-GOV-00A package-register review closed at 70 execution units. Three
stateful Pure surfaces discovered during review—ERMiT export, RQ Info Details,
and DEVAL loading—were added rather than misclassified as read-only reports.
Both register reviewers confirmed closure-ready with no remaining high/medium
findings. The operator subsequently clarified that every included item is a
binding `contractual / unverified` obligation now; missing child/contract/
manifest/revision evidence limits conformance claims but never makes scope
optional.

The current register contains 73 execution units because GOV-00A is the fourth
governance unit and REM-01 plus REM-02 are bounded remediation units. GOV-00A ratifies the contractual/evidence/execution model
before shared foundations begin; the prior 70-unit review remains historical
population/boundary evidence rather than the current total.

GOV-00A Milestone 1 is now partially active. Root, WEPPcloud, controller, and
rq-engine agent governance records contract-first precedence; canonical schema
and registry publication plus dual review remain open.

REM-01 is complete. Its contract checkpoints are
`1afa57fd6d63b93688057143ec5c45daa6f3170f` and
`57ea1a3e2e71073f65e45c4af1cc607b2323ef37`; its final contract/state and
security/regression reviewers approved with no findings, and its stable-tree
repository sweep passed 5,070 tests with 58 skipped. This completion supplies
evidence to the later DOM-02, DOM-25A, and DOM-25B audits but leaves all three
owners planned.

REM-02 is proposed under its own GOV-00A-M1B authority milestone. It may not
reuse M1A or advance SURF-06; its contract decision and independent reviews must
be committed as a standalone ancestor before implementation begins.

At final closure, summarize total in-scope controllers, verified/excluded counts,
defects found, tests added, compatibility decisions, packages closed, review
findings by severity, remaining operator-accepted risks, and the cost of ongoing
maintenance. State honestly which configurations and legacy saved-run versions
were exercised.

## Context and Orientation

Pure UI controller source lives primarily in
`wepppy/weppcloud/controllers_js/`. The generated browser bundle is
`wepppy/weppcloud/static/js/controllers-gl.js`; it is built from source by
`build_controllers_js.py` and must not be edited directly. Pure templates live
primarily in `wepppy/weppcloud/templates/controls/`, but nested advanced options,
modals, map partials, headers, and standalone routes also participate.

A typical state-changing flow is:

    Jinja macro arguments
      -> rendered input id/name/value/data hooks
      -> controller selector and FormData/JSON serialization
      -> browser/session or rq-engine endpoint
      -> parse_request_payload normalization
      -> NoDb/server mutation under persistence/locking rules
      -> optional RQ enqueue and worker execution
      -> response, StatusStream, polling, and domain events
      -> saved state and bootstrap/reload hydration

The same token does not necessarily name every layer. A DOM id is a selector and
label target; a form name is the submitted key; an option value is an API token;
a human label is presentation; a persisted attribute can have a different
internal name. A contract must map these explicitly rather than normalizing them
to one convenient column.

`docs/ui-docs/controller-contract.md` is the current shared invariant document.
`docs/ui-docs/control-ui-styling/control-inventory.md` is useful historical
reconnaissance but is not trusted as current without source/runtime evidence.
The umbrella audit register is the initiative population authority once its
first milestone is dual-reviewed.

## Plan of Work

### Milestone 1: Freeze the population and ratify the standard

Generate the actual bundle module list from `_collect_controller_modules()` and
reconcile it with bootstrap/controller registration, Pure macro-importing
templates, run configuration/mod gates, and standalone Pure consoles. For each
domain controller, record source, rendered host, routes, mutation owner, RQ
worker, tests, risk tier, and stable child-package ID. Mark infrastructure
helpers and read-only components as shared or excluded only with a parent
contract and rationale. Freeze `artifacts/child_package_register.md` only after
both inventory reviewers confirm complete allocation.

Execute GOV-00A to create `docs/ui-docs/contracts/README.md` from the schema in
the child audit prompt. It is the normative standard and derived published
reader index. Separate binding coverage status (`contractual` or explicitly
`excluded`) from evidence grade (`unverified`, `documented`, or `verified`) and
from package execution state. Define required contract sections, evidence
levels, canonical ownership, contract-first checkpoints, compatibility/
deprecation, and review gates. `contract-obligations.json` becomes the sole
machine scope/owner/evidence/revision summary and source for
`tools/ui_contract_ratification.py write-index`. The audit ledger remains a
reviewed discovery projection that key-reconciles exactly; the child register
continues to own execution boundaries and state. Update the general controller
contract only where needed to link the standard and clarify the `id`/`name`
distinction.

Dispatch Reviewer A to challenge population completeness and Reviewer B to
challenge evidence/maintenance rules. Disposition all findings before freezing
the register. Expected evidence is a deterministic inventory command/output,
not a manually remembered controller list.

Milestone acceptance: every discovered item has a row or explicit exclusion,
the standard passes documentation lint, both reviews are closed, and the
umbrella tracker names the approved WATAR pilot scope.

### Milestone 2: Execute the WATAR/Ash pilot package

Instantiate `controller_contract_audit_iteration_prompt.md` as a new child work
package. Capture representative rendered Ash HTML and exact serialized payloads
for Srivastava 2023 and Watanabe 2025, static and dynamic transport, all depth
modes, and uploads. Trace selector public labels, internal model tokens, input
ids and submitted names, per-model cache behavior, rq-engine parsing, NoDb state,
worker use, persisted reload, and completion/error paths.

Preserve the known regression as a test that independently asserts DOM ids and
submitted names, plus backend mutation and saved/reloaded values. Correct only
confirmed remaining mismatches. Publish
`docs/ui-docs/contracts/ash.md`, update stale domain links, run frontend/backend
gates, and complete the required contract/code and regression/QA reviews.

Milestone acceptance: the Ash register row is `verified`, both reviews are
dispositioned, and the pilot retrospective identifies stable metadata for an
automated coverage check.

### Milestone 3: Add lightweight coverage enforcement

Using only metadata demonstrated stable by the pilot, add
`docs/ui-docs/contracts/manifest.yaml` (or an equivalently reviewable repository-
owned format) mapping each domain contract to its template/controller/route/
NoDb/RQ source paths and contract test paths. Shared macros/helpers list every
consumer so their source changes fan out to mapped contracts.

Add a deterministic repository-owned check, for example
`tools/check_ui_contract_coverage.py`, with full-coverage and change-aware modes.
Full coverage checks rows, contracts, required headings, source/test path
existence, status, revision/date, and named evidence. Change-aware mode compares
a selected base revision and requires every mapped source change to include its
canonical contract and relevant contract-test change. The only exception is a
package-scoped no-contract-impact attestation that names the diff and evidence
and is confirmed by both independent reviewers. Attestations are explicit
exceptions, not silent skips.

Prefer a small repository-owned script or test over a new dependency. Do not
attempt to parse JavaScript/Jinja semantics with fragile regular expressions and
call that end-to-end proof.

Wire the check into the narrowest canonical validation surface and document its
command. The check should prevent omissions and stale metadata, while controller-
specific tests prove field behavior.

Milestone acceptance: a missing contract/register row fails predictably; a
mapped source-only change fails; a shared macro/helper change fans out to all
mapped consumers; a valid dual-reviewed attestation is accepted; stale or
unsigned attestations fail; the complete pilot state passes; and dual review
findings are closed in the relevant child package.

### Milestone 4: Execute remaining registered packages iteratively

At each iteration, select the next highest-risk `contractual / unverified` row
or cohesive low-risk family. Create its child package, add it to all trackers,
execute the reusable prompt end to end, close both reviews, advance its evidence
grade, and only then select the next package. Do not open enough authoring packages to create shared-
worktree collisions; read-only reconnaissance may run in parallel.

Prioritize boundaries most likely to silently corrupt user intent: enum/select
tokens, macro `id`/`name` differences, unchecked/disabled/hidden values, dynamic
rows, file uploads, legacy aliases, persisted configuration, config-gated
defaults, and RQ completion. Shared infrastructure changes require impact review
against all verified consumers.

At the end of each dependency/risk batch, run the coverage check, review register
completeness, update the umbrella Progress/Surprises/Decisions, and publish a
short summary. If a defect spans multiple registered boundaries, stop expansion
and create a separate scoped remediation package.

Milestone acceptance per iteration: child package closed, canonical contract
verified at a named revision, tests/evidence recorded, security gate satisfied,
both reviews dispositioned, register and trackers current.

### Milestone 5: Consolidate documentation and close the initiative

Replace current-authority links to missing or archived plans with canonical
contracts. Retain archived plans as historical rationale and label them as such.
Make `controllers_js/README.md`, `controllers_js/AGENTS.md`, relevant domain
READMEs, and `docs/ui-docs/README.md` describe the maintenance workflow without
duplicating field matrices.

Run initiative-wide coverage, documentation, frontend, focused backend, and full
suite gates. Dispatch two final independent reviewers: one for population and
semantic contract completeness, one for regression/security/operability risk.
Disposition findings, record residual risk, move active prompts to completed,
and close the package and `PROJECT_TRACKER.md` entry.

Milestone acceptance: every row is verified or explicitly operator-approved as
excluded, no high/medium review findings remain, and outcomes state exercised
and unexercised configs truthfully.

## Concrete Steps

Run commands from `/home/workdir/wepppy` unless a child ExecPlan says otherwise.

Baseline and inventory commands include:

```bash
git status --short
python -c 'from wepppy.weppcloud.controllers_js.build_controllers_js import _collect_controller_modules; print("\n".join(_collect_controller_modules()))'
rg -l 'controls/_pure_macros.html' wepppy/weppcloud
rg --files wepppy/weppcloud/routes | rg 'templates/.*(pure|console|dashboard)'
rg -n 'getInstance|window\.[A-Z].*=|bootstrap' wepppy/weppcloud/controllers_js
rg -n 'parse_request_payload' wepppy/weppcloud/routes wepppy/microservices/rq_engine
```

For each child package, use the reusable prompt and record exact focused test
commands rather than placeholders. Common validation entry points are:

```bash
wctl run-npm lint
wctl run-npm test
python wepppy/weppcloud/controllers_js/build_controllers_js.py
wctl run-pytest tests/<focused-path>
wctl run-pytest tests --maxfail=1
wctl doc-lint --path docs/ui-docs/contracts/<controller>.md
wctl doc-lint --path docs/work-packages/<child-package>
python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
git diff --check
```

If queue wiring changes, also run `wctl check-rq-graph` and follow the repository
manual live-job-tree validation contract. Preview spelling normalization with
`diff -u <file> <(uk2us <file>)` before accepting any rewrite.

## Validation and Acceptance

The initiative is accepted only when a fresh checkout can run the contract
coverage command and account for every in-scope Pure UI domain controller. Each
accounted controller must link to a canonical file that names its verified
source revision/date and executable evidence.

For state-changing controllers, inspection alone is insufficient. Acceptance
requires representative rendered HTML or equivalent template-render evidence,
the actual browser payload, normalized server inputs, documented state mutation,
and persisted/reloaded results where durable state exists. RQ controllers also
require enqueue and terminal success/error evidence. Configuration-dependent
coverage must be enumerated.

Every submitted, hydrated, persisted, enum/file-bearing, hidden/disabled-
sensitive, or RQ-controlling value is material by default. Verification requires
a per-field, per-mode, per-configuration evidence matrix. Exclusions require a
written rationale and both reviewers. Untested material variants and unresolved
material discrepancies remain `documented`, not `verified`.

Every child package and the umbrella closeout require two independent reviews.
No unresolved high/medium finding may be silently moved to follow-up. Operator
acceptance is required for residual high/medium risk.

## Idempotence and Recovery

Inventory and coverage commands are read-only and repeatable. Contract updates
are ordinary Markdown edits. Child implementation must begin from recorded
baseline evidence and use focused commits or clearly bounded diffs so a failed
repair can be reverted without discarding unrelated work.

If a rendered fixture or saved-run sample contains sensitive/project-specific
data, record only the minimum sanitized field evidence and do not commit uploads,
tokens, or full run state. If a child audit discovers that its assumed boundary
is wrong, leave its register row `auditing`, record the discovery, revise the
child ExecPlan, and split the package rather than forcing closure.

Generated controller bundles are rebuilt only after source changes. Do not hand-
edit or use them as the sole baseline. Never use destructive reset/checkout to
recover a shared worktree.

## Artifacts and Notes

The umbrella package owns:

- `artifacts/controller_audit_register.md` - item population and status;
- `artifacts/child_package_register.md` - stable execution boundaries,
  dependencies, risks, and exclusions;
- `artifacts/<date>_contract_review.md` and
  `artifacts/<date>_regression_qa_review.md` - raw/verbatim independent reviews;
- `artifacts/<date>_scaffold_review_disposition.md` - primary disposition and
  post-fix reviewer confirmations;
- later package-batch and final review summaries;
- `notes/` for bounded inventory outputs that are too detailed for the tracker.

Each child package owns its baseline evidence, canonical contract changes, test
evidence, security review when applicable, two raw/verbatim review artifacts,
and primary disposition. Do not copy large logs into the ExecPlan; summarize
them and link the artifact.

## Interfaces and Dependencies

This package introduces documentation and process interfaces before code:

- `docs/ui-docs/contracts/README.md` becomes the normative contract schema,
  maintenance policy, and derived/published reader index; it is not a competing
  editable coverage-status authority.
- `docs/ui-docs/contracts/contract-obligations.json` becomes the sole machine
  authority for obligation scope, execution owner, evidence grade, canonical
  contract path, and revision/date summary and supplies the generated index.
- `docs/ui-docs/contracts/manifest.yaml` becomes only the
  source/contract/test/shared-consumer mapping authority used by GOV-01's
  change-aware gate.
- `docs/ui-docs/contracts/<controller>.md` becomes domain authority.
- `artifacts/controller_audit_register.md` remains the reviewed discovery/
  source/host/producer projection and must key-reconcile to the obligation
  registry.
- `artifacts/child_package_register.md` becomes execution-boundary authority.
- `controller_contract_audit_iteration_prompt.md` defines child execution and
  review gates.
- `docs/ui-docs/controller-contract.md` remains shared runtime invariants.

The initiative depends on repository-owned Jinja templates, browser controller
source, route parsers, NoDb/RQ state, Jest/jsdom, pytest, `wctl`, and Markdown
tooling. Do not add an external dependency for inventory or contract checking
without satisfying `docs/standards/dependency-evaluation-standard.md`.

Revision note (2026-07-17): Initial ExecPlan authored from the operator's
contract-maintenance request and the WATAR regression precedent.
