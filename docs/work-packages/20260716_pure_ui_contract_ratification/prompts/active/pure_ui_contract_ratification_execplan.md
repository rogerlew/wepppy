# Ratify the Pure UI contract standard and binding coverage model

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must remain current
as work proceeds. Maintain it in accordance with
`docs/prompt_templates/codex_exec_plans.md`.

This is the active ExecPlan for GOV-00A under the umbrella
`docs/work-packages/20260716_pure_ui_contract_standardization_c/`. The umbrella
plan remains active for program coordination; this child plan exclusively owns
standard ratification. Update both package trackers at every stopping point.

## Purpose / Big Picture

After this package, a maintainer can open `docs/ui-docs/contracts/README.md` and
know exactly what a Pure UI contract must contain, which file is authoritative,
and what evidence is required before behavior is called verified. Every item in
the parent coverage ledger is contractually in scope immediately. An incomplete
test or endpoint matrix is visible as unverified work; it cannot be used to
ignore or silently exclude the surface.

The outcome is observable through repository documentation and deterministic
checks: included rows use `contractual`, forbidden `candidate` inclusion fails,
required contract sections are enforced, the derived reader index does not
compete with the ledger/manifest/domain authorities, and both independent
reviewers approve the standard.

## Progress

- [x] (2026-07-17 01:48 UTC) Created GOV-00A package, tracker, and active
  ExecPlan from explicit operator direction.
- [x] (2026-07-17 01:48 UTC) Changed the parent ledger to binding
  `contractual / unverified` semantics.
- [x] (2026-07-17) Completed two independent scaffold reviews, dispositioned all
  findings, and received post-fix closure confirmation from both reviewers.
- [ ] Ratify authority hierarchy and lifecycle vocabulary.
- [ ] Publish the normative README and reusable contract template.
- [ ] Add deterministic governance validation and negative fixtures.
- [ ] Reconcile umbrella/developer/historical documentation.
- [ ] Complete dual implementation review, record outcomes, and archive this
  ExecPlan.

## Surprises & Discoveries

- Observation: A single lifecycle status cannot express both binding scope and
  implementation evidence.
  Evidence: The operator rejected `candidate` because future agents could treat
  it as non-contractual even though the row's boundary and owner were frozen.

- Observation: The future contracts README has been described as both a
  normative schema and a coverage index, while the parent ledger and future
  manifest also own coverage data.
  Evidence: Authority notes in the parent controller audit register, child
  register, and umbrella ExecPlan.

Add discoveries with exact paths, commands, or concise output. Do not erase
historical discoveries when later evidence changes a decision.

## Decision Log

- Decision: Use three independent dimensions: contractual scope, evidence
  grade, and package execution state.
  Rationale: A binding contract may be unverified, and a planned package does
  not make the obligation optional. Conflating these concepts recreates the
  ambiguity the package exists to remove.
  Date/Author: 2026-07-17 / Operator direction, recorded by Codex.

- Decision: `docs/ui-docs/contracts/README.md` is normative for schema and
  lifecycle but derived for per-controller coverage/status listings.
  Rationale: The coverage ledger, future machine manifest, and domain contracts
  need distinct named authority. A second hand-edited status table would drift.
  Date/Author: 2026-07-17 / Codex, subject to dual review.

- Decision: `docs/ui-docs/contracts/contract-obligations.json` is the sole
  machine authority for each obligation's stable key, contractual scope,
  execution owner, evidence grade, canonical contract path, and verified
  revision/date summary.
  Rationale: Positive enforcement and a derived index need one deterministic
  source. The parent ledger remains reviewed discovery/history, domain files own
  normative behavior and detailed evidence, and GOV-01 later adds source/test
  fan-out without duplicating obligation status.
  Date/Author: 2026-07-17 / Codex, from scaffold review A and B findings.

- Decision: Ratification precedes shared-foundation contracts and WATAR.
  Rationale: Those packages need a stable schema and evidence vocabulary before
  their output can be reviewed consistently.
  Date/Author: 2026-07-17 / Codex.

## Outcomes & Retrospective

The package is scaffolded but not executed. No canonical schema or template may
be described as ratified until the milestones, validation, disposition, and
post-fix reviews below are complete.

At closure, summarize the exact authorities created, validation behavior,
review findings, deliberately deferred GOV-01 enforcement, and any unresolved
operator-accepted risk. State explicitly that ratification binds coverage but
does not verify controller implementations.

## Context and Orientation

Pure UI browser controllers live primarily in
`wepppy/weppcloud/controllers_js/`, templates in
`wepppy/weppcloud/templates/` and route-local template directories, server
normalization in WEPPcloud/rq-engine routes, durable state in NoDb controllers,
and asynchronous execution in `wepppy/rq/`. The parent package already
reconciles 33 run bootstrap entries, 56 bundled modules, shared producers, and
stateful standalone surfaces.

The authority files after ratification are:

- `docs/ui-docs/contracts/contract-obligations.json`, which binds stable
  obligation keys, included scope, execution owner, evidence grade, canonical
  contract path, and verified revision/date summary;
- `artifacts/controller_audit_register.md`, which records reviewed discovery,
  source/host evidence, and producer/parent ownership and must reconcile exactly
  to the obligation registry;
- `artifacts/child_package_register.md`, which binds execution boundaries and
  dependencies;
- the future GOV-01 manifest, which separately maps source, contract, test, and
  shared-consumer fan-out;
- each `docs/ui-docs/contracts/<domain>.md`, which will own normative domain
  behavior and evidence at a named revision.

In this plan, `contractual` means a surface is unconditionally in scope.
`Unverified` means required conformance evidence is missing. `Documented` means
a canonical behavior contract exists but some verification gates remain.
`Verified` means generated/runtime evidence, focused tests, a named revision,
and dual review support the conformance claim. `Planned`, `auditing`, `blocked`,
and `closed` describe package work, not contract force.

Evidence-grade transitions are normative. `unverified -> documented` requires a
canonical contract and both contract reviews. `documented -> verified` requires
the named generated/runtime evidence, focused tests, revision/date, and post-fix
review. Mapped source or test drift, a material discrepancy, invalidated
fixture, or withdrawn evidence demotes `verified -> documented` and reopens the
owning child package; loss of the normative contract blocks validation rather
than removing scope. Scope can move from `contractual` to `excluded` only with
explicit operator approval and dual review. Before GOV-01 automates drift
detection, every relevant source change performs this assessment manually.

Execution-state mapping is also normative. `planned` means no child execution is
active; `auditing` means the child package is Open with work In Progress;
`blocked` means its tracker satisfies the repository blocked threshold; and
`closed` requires a closed package, completed ExecPlan, validation, and both
reviews. The parent child-package register owns this state; child trackers
provide detail but cannot silently contradict it.

Evidence promotion/demotion is one atomic repository change: update the
obligation registry summary, canonical domain contract evidence section, named
tests/evidence, and parent ledger projection together. `write-index` then
regenerates the README block from the registry. `check` rejects a `verified`
record without revision/date and named evidence, any domain/registry mismatch,
or a stale generated block. Review dispositions record who authorized the
transition; they do not become a second status authority.

## Plan of Work

### Milestone 1: Ratify authority and lifecycle

Create `docs/ui-docs/contracts/README.md` and
`docs/ui-docs/contracts/contract-obligations.json`. Define the authority hierarchy and
the three independent status dimensions in normative language. State that every
included parent-ledger row is contractual immediately and that removal or
exclusion requires explicit operator approval plus dual review. Define how the
README publishes a derived reader index without becoming a competing editable
coverage table. The generated block is delimited by
`<!-- BEGIN GENERATED PURE UI CONTRACT INDEX -->` and
`<!-- END GENERATED PURE UI CONTRACT INDEX -->` and is written only from the
obligation registry by `tools/ui_contract_ratification.py write-index`.

Give every included ledger row a stable obligation key and enumerate it exactly
once in the JSON registry. Each record requires
`contract_scope="contractual"`, one of `unverified|documented|verified`, a
registered execution-owner ID, a canonical contract path, and revision/date
fields whose nullability is defined by evidence grade. The checker must reject
missing, blank, optional, improperly excluded, duplicate, unknown-scope,
unknown-grade, and unknown-owner records. The ledger and registry key sets must
match exactly.

Update `docs/ui-docs/controller-contract.md` only where necessary to point to
the ratified schema and preserve shared runtime invariants. Reconcile the parent
ledger, child register, child audit prompt, package docs, and relevant AGENTS or
README guidance. Preserve raw historical reviews without rewriting their
then-current vocabulary; add supersession notes in current authority docs.

Milestone acceptance: no current authority describes an included item as a
candidate; searches distinguish historical raw artifacts from current rules;
the hierarchy has one owner for schema, item coverage, execution boundaries,
machine mapping, and domain behavior; both reviewers close all findings.

### Milestone 2: Ratify the canonical contract schema

Add `docs/ui-docs/contracts/_contract_template.md`. Require
identity/owner/config/security fields; rendered DOM id/name/type/default/label/
unit/data hooks; hidden/disabled/unchecked/empty/absent semantics; controller
selectors, hydration, caching, events, and serialization; transport method/URL/
encoding/auth/CSRF; parser keys/types/defaults/aliases/conflict precedence;
mutation owner/locking/dump/invalidation; RQ enqueue/dependencies/terminal/error;
reload/old-run compatibility; observed-versus-normative discrepancies; tests,
manual evidence, named revision/date, and review disposition.

Use WATAR's known `id` versus submitted `name` failure as a schema fixture, not
as a domain audit. The example must show labels, enum tokens, parser keys, and
persisted attributes as distinct values. Do not assert that current WATAR
behavior is verified in this package.

Milestone acceptance: the template can represent WATAR, a shared producer, a
read-only shell, and an RQ-backed surface without changing headings; every
material value/configuration has an evidence slot; N/A requires rationale and
dual review.

### Milestone 3: Make ratification testable

Add `tools/ui_contract_ratification.py` with `check` and `write-index`
subcommands. Add `tests/tools/test_ui_contract_ratification.py` and isolated
fixtures under `tests/fixtures/ui_contract_ratification/`. `check` positively
enumerates every ledger/registry obligation and requires exactly contractual
scope, an allowed evidence grade, a registered owner, and a unique key. It also
rejects missing required contract-template sections and a hand-edited generated
index that disagrees with `contract-obligations.json`.

Negative fixtures operate on temporary copies and assert distinct diagnostic
codes: `missing_obligation`, `blank_contract_scope`,
`invalid_contract_scope`, `improper_exclusion`, `duplicate_obligation`,
`invalid_evidence_grade`, `unknown_execution_owner`,
`missing_required_section`, and `index_out_of_sync`. Current-authority inputs
are an explicit allowlist: the obligations JSON, controller ledger, child
register, contracts README/template/domain files, and the finite developer docs
named by this plan. Raw review artifacts are immutable evidence, are never
validator inputs, and must not be rewritten to remove historical vocabulary.

Keep GOV-01's base-revision diffing, shared-producer fan-out, and same-change
source enforcement out of this package. Record the exact schema/interface GOV-01
will consume so the later package does not reverse-engineer prose.

Milestone acceptance: positive fixtures pass; each required negative fixture
fails for the intended reason; documentation lint passes; dual reviewers agree
the checks enforce obligation without falsely claiming runtime verification.

### Milestone 4: Reconcile authority and close

Update this finite authority set:
`docs/ui-docs/controller-contract.md`, `docs/ui-docs/README.md`,
`wepppy/weppcloud/controllers_js/README.md`,
`wepppy/weppcloud/controllers_js/AGENTS.md`, the parent package's package,
tracker, active ExecPlan, controller ledger, child register, child audit prompt,
this GOV-00A package, and `PROJECT_TRACKER.md`. Do not rewrite archived plans or
raw reviews; label or redirect current-authority links only.

Dispatch two independent implementation reviewers. Reviewer A traces contract
semantics and authority. Reviewer B challenges drift prevention, negative
tests, executability, and whether unverified could still be read as optional.
Disposition every finding, obtain post-fix confirmation, run final docs and
targeted checks, move this ExecPlan to `prompts/completed/`, and close GOV-00A.

Milestone acceptance: no unresolved high/medium findings, all checks pass,
authority links are current, and SHR-01 is unblocked.

## Concrete Steps

Run commands from `/home/workdir/wepppy`.

Inventory current authority and vocabulary:

    rg -n 'candidate|contractual|unverified|documented|verified|coverage authority' \
      docs/ui-docs/controller-contract.md docs/ui-docs/README.md \
      wepppy/weppcloud/controllers_js/README.md \
      wepppy/weppcloud/controllers_js/AGENTS.md \
      docs/work-packages/20260716_pure_ui_contract_standardization_c/package.md \
      docs/work-packages/20260716_pure_ui_contract_standardization_c/tracker.md \
      docs/work-packages/20260716_pure_ui_contract_standardization_c/artifacts/controller_audit_register.md \
      docs/work-packages/20260716_pure_ui_contract_standardization_c/artifacts/child_package_register.md
    markdown-extract 'Status|Authority|Contract' \
      docs/work-packages/20260716_pure_ui_contract_standardization_c/artifacts/controller_audit_register.md

Validate package documentation during execution:

    PATH=/home/workdir/wepppy/.venv/bin:$PATH wctl doc-lint \
      --path docs/work-packages/20260716_pure_ui_contract_ratification
    PATH=/home/workdir/wepppy/.venv/bin:$PATH wctl doc-lint \
      --path docs/ui-docs/contracts
    PATH=/home/workdir/wepppy/.venv/bin:$PATH python \
      tools/ui_contract_ratification.py check
    PATH=/home/workdir/wepppy/.venv/bin:$PATH wctl run-pytest \
      tests/tools/test_ui_contract_ratification.py
    git diff --check

Run the focused governance tests introduced by Milestone 3 using their exact
path, followed by applicable docs and full-suite checks recorded in the tracker.
Do not use placeholder test paths in closeout evidence.

## Validation and Acceptance

A fresh checkout must be able to determine from current authority that all
included parent-ledger rows are contractual. A deterministic check must fail if
one is changed to `candidate`. The canonical template must expose every layer
from rendered DOM through reload and require explicit N/A rationale where a
layer does not apply.

The package is accepted only when the normative README, template, authority
links, and governance checks agree; both independent reviews are dispositioned;
and documentation/test commands pass. Ratification is not runtime verification:
no controller advances to `verified` without its own child-package evidence.

## Idempotence and Recovery

Documentation inventory and validation are read-only and repeatable. Make
ordinary Markdown or small repository-owned test changes; do not generate or
hand-edit browser bundles. If schema fields prove unstable, record the discovery
and revise this plan before changing authority. Never weaken contractual scope
to make a test pass. Revert only package-owned edits and preserve unrelated
worktree changes.

## Artifacts and Notes

Store raw scaffold and implementation reviews under `artifacts/`, with a
separate primary disposition and post-fix confirmations. Keep concise validation
transcripts in the tracker or a bounded artifact. Do not copy large source or
test logs into this plan.

## Interfaces and Dependencies

GOV-00A produces the schema/lifecycle interface consumed by SHR-01 through
SHR-04B, DOM-01, and GOV-01. The normative README owns schema and lifecycle.
`contract-obligations.json` is the sole machine authority for obligation scope,
owner, evidence grade, canonical path, and revision/date summary. The parent
ledger is the reviewed discovery/source/host/producer projection and must
key-reconcile exactly. The child register owns execution boundaries and state;
domain contract files own normative behavior and detailed evidence; GOV-01's
future manifest owns source/contract/test/shared-consumer mapping only.

No new external dependency is authorized. Use repository Markdown tooling,
small repository-owned checks, Jest/pytest only where relevant, and `wctl`
wrappers for canonical validation.

Revision note (2026-07-17): Initial GOV-00A ExecPlan authored from the
operator's direction that all registered Pure UI items are contractual now.
