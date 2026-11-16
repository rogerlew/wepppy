# Preserve accepted work through remote integration and release


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Maintain
Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective.
The operator requested execution on 2026-11-16; recommended defaults are adopted. Work in `/workdir/wepppy` and preserve existing dirty/untracked files.

## Purpose / Big Picture


An accepted local implementation must not silently vanish when another task
updates master. Operators should be able to distinguish local acceptance, remote
integration, successful validation of the integrated tree, and release eligibility.
The proof must come from Git objects, actual check execution, and settings readback,
not issue status or an agent's recollection. Initial scope is accidental history
loss and unreviewed security regressions, not containment of a repository owner
who can deliberately disable every control.

## Progress


- [x] (2026-11-16 20:48 UTC) Capture actual dropped-history topology and recovery.
- [x] (2026-11-16 20:48 UTC) Scaffold package, tracker, and consumer inventory.
- [x] (2026-11-16) Dispatch Git/history, security/CI, and correctness/QA reviewers.
- [x] (2026-11-16) Consolidate three independent reviews and record D1–D5
  in `artifacts/review_synthesis.md`; no enforcement is claimed.
- [x] (2026-11-16) Adopt recommended D1–D5 defaults and promote the canonical
  integration-history standard; no independent human approver is yet assigned.
- [x] (2026-11-16) Implement and validate remote receipt and local protected-ref guard.
- [x] (2026-11-16) Prove wrong-checkout rejection using live mount identity;
  adopt task ownership and serialized integration/validation.
- [x] (2026-11-16) Canary rejected workflow weakening and no-PR updates,
  accepted eligible PR-associated integration, and master protection was read back.
- [x] (2026-11-16) Bind publication/deployment eligibility to exact validated
  source; stale approval failed before publish, then qualified publication succeeded.
- [x] (2026-11-16) Complete independent implementation reviews and close findings.
- [x] (2026-11-16) Complete disposable recovery drill: refused ref rewrite, external WIP recovery, legitimate merge and fresh receipt.
- [x] (2026-11-16) Repair actual pack-refs false positive; 37 real-Git tests, independent review and shared-checkout ref-preserving maintenance pass.
- [x] (2026-11-16) Record failed full/remainder results; repair YAML test pollution and plan boundary; coupled 559 and deployment 77 pass. Four preexisting RQ fixture failures remain.
- [x] (2026-11-16) Integrate native policy reporter through protected PR #662; repeated-event positive and green-but-weakened negative canaries pass with unchanged master protection.
- [x] (2026-11-16) Resolve four RQ fixture mismatches on operator request; affected 81 tests pass, adjacent 19 pass/36 skip; no production behavior changes.
- [ ] Finish the five-real-integration observation period before package closure.

## Surprises & Discoveries


The remote did not see a parser deletion. The original soils commit `cd90ee1aa`
was based on accepted tip `4194fd43b`; rebased soils commit `7755822d7` was based
on remote `ff1740239`. Thus force-push prohibition and changed-path CI alone cannot
prevent this incident. Reflog proves outcomes, not exact command arguments or actor.

Reviewers found that `tools/wctl2/commands/python_tasks.py` directs tests to the
container's `/workdir/wepppy`. A task's shell worktree is not proof that its code
was tested. They also found common-image publication triggered by master push
without waiting for an exact-candidate acceptance gate.

## Decision Log


2026-11-16: preserve original reviewed history, use no new service, and implement
small verifiers atop existing Git/CI tools after decisions. Local hooks are
accident guards and must not be described as a malicious-agent boundary.

D1–D5 in `package.md` were adopted by the execution request. Use
merge-preserving integration for initial exact-SHA receipts, one designated
integrator, and serialized validation on the existing stack. A worktree does not
create an independent ref namespace or container environment. The canonical standard and root branch-policy pointer now authorize scoped task
branches and define one integrator.

## Outcomes & Retrospective

The implementation is wired and remotely enforced. Bootstrap PR #657 preserved
accepted source through merge98017d789; protected PR #661 integrated the sparse
checkout correction as d3b0effbc. Fresh remote ancestry receipts and settings
readback are retained in this package. Independent implementation reviews closed
all identified medium/high findings. No production deployment occurred.

Local guards now survive task worktree/venv removal, and checkout verification
recognizes sparse trees. Actual GitHub canaries rejected a green-but-weakened
workflow and a no-PR commit, and accepted a valid PR-associated update. GitHub may
fast-forward an eligible PR head and record it as merged; this is not merge-button
or API-only enforcement. A separate failed canary setup was isolated and closed,
and is explicitly excluded from positive evidence.

Full application attempts and regression repairs are recorded; the four RQ fixture
failures were subsequently repaired and passed scoped validation. No clean
full-suite pass is claimed. The
five-real-integration observation period remains open. Do not close the package
or substitute artificial canary updates for that operational evidence.
## Context and Orientation


Read root `AGENTS.md`, `docs/work-packages/README.md`,
`docs/standards/hardening-lifecycle-standard.md`, and
`docs/standards/generated-artifact-validation-standard.md`. Read
`.github/workflows/AGENTS.md` before workflow changes; canonical workflow sources
are under `.github/forest_workflows/`, with generated copies under
`.github/workflows/`. Inspect `scripts/build_forest_workflows.py`,
`.github/workflows/publish-weppcloud-image.yml`, auxiliary publication, and
`scripts/deploy-production.sh` rather than inventing a parallel release mechanism.

A receipt is a durable record of accepted source SHA, observed remote target SHA,
repository/branch identity, observation time, supported integration mode, ancestry
or explicit mapping result, and validation evidence. Its exact schema and consumer
must be ratified. A historical receipt is not a permanent assertion about a moving
branch. Store it after acceptance; do not require a commit to contain its own hash.

## Plan of Work


### M0 — Ratify contract and inventory consumers

Resolve D1–D5 against `artifacts/review_synthesis.md`. Create
`docs/standards/integration-history-governance.md` and update the package/closure
templates to distinguish locally accepted, integrated, validated, and released.
Select receipt storage, supported merge mode, operator recovery, and publishing
semantics. Inventory every closure, master-update, baseline and release consumer
in `artifacts/incident_and_consumers.md`, preserving unverified dispositions until
examined. Export existing settings before proposing an exact remote configuration.
M0 ends with a reviewable contract and concrete configuration, not a settings change.

### M1 — Remote receipts and local history preservation

Implement the smallest proposed verifier in `tools/check_integration_history.py`
with tests in `tests/tools/test_integration_history.py`. Names are proposed paths,
not existing commands. Fetch the explicit remote target into an isolated temporary
ref, bind validation to that immutable observed commit, and reject missing accepted
objects, unpushed accepted revisions, unsupported merge mode, or unavailable remote
truth. Never treat stale `origin/master`, a cached green status, or a shallow-history
failure as success. Record whether remote movement requires retry under the ratified
snapshot/freshness contract; avoid claiming an atomic observation across GitHub APIs.

For shared master, prohibit routine rebase/reset and test a supported update path
that preserves existing accepted ancestors. Evaluate the smallest local guard
(wrapper plus installed hook/ref-transaction guard if justified) against rebase,
reset, branch replacement and hook bypass. Preserve Git LFS/existing hooks; expose
missing installation explicitly. Do not claim shell aliases or editable hooks
prevent a credentialed actor from bypassing policy. Tests use real bare remotes and
clones to reproduce both valid updates and the actual incident topology.

### M2 — Task isolation and tested-checkout identity

After D2 adoption, define task worktree/branch ownership and serialize master
integration. Do not switch another task's checkout or remove its worktree/stash.
Before a wctl test counts as evidence, compare host candidate identity/content with
what the running container consumes. Test that the wrong worktree is rejected.
Begin with serialized validation on the existing stack; do not introduce one Compose
stack per task without evidence that this smaller approach fails. Cover concurrent
remote updates, dirty tracked and untracked files, shared refs, and abandoned tasks.

### M3 — Remote rules and trusted baseline gate

Prepare the exact supported GitHub rules/protection payload, named required check,
review requirements, bypass inventory, and recovery procedure. Prove the check runs
and reports on every candidate, including docs-only changes, before making it required.
Use PR integration as the proposed default; decide how a solo maintainer can satisfy
review without pretending agents using the same identity are independent approvers.
Baseline policy must be compared with an approved base/trusted source so a candidate
cannot simply delete its own assertion and report green. Protected policy changes
need explicit retirement/upgrade review, not an eternal prohibition on legitimate
architecture changes. No restriction can contain the account owner who controls it.

First exercise policy fixtures/readback and an authorized disposable canary where
available. Do not enable live rules or create deliberately failing remote branches
without authorization. After authorized enablement, retain exact readback and evidence
of ordinary accepted integration and rejected nonconforming integration. An exported
JSON proposal alone is not enforced status.

### M4 — Publication, recovery, and closure

Inspect common-image, auxiliary-image, manual dispatch and deploy entry points.
Before registry writes or release eligibility, bind evidence to the exact candidate
SHA/artifact, never a branch name that may move. Determine whether unqualified artifacts
may be published at all under D5; recommended default is gating publication itself.
Exercise failure before publication, stale approval, policy change, later parser
revert, failed check, missing check, operator exception, and interrupted retry.
No production deployment or registry write is needed for local failure tests.

Complete independent implementation correctness, QA and security reviews, all
required repository tests, an authorized enforcement canary, and the agreed recovery
observation window. Preserve recovery refs and receipts until explicit retention
criteria permit retirement. Promote durable rules outside the package before closure;
leave historical packages unchanged.

## Concrete Steps


From `/workdir/wepppy`, begin read-only with `git status --short`,
`git log --graph --oneline -30`, and the retained incident artifact. Use `gh api`
read-only settings commands only when the available GitHub connector lacks that
capability. Do not use force-push, hard reset, clean, or branch switches on shared WIP.

After implementation, run `wctl run-pytest tests/tools/test_integration_history.py`
and the affected existing deployment/wctl suites. Run
`python3 scripts/build_forest_workflows.py --check` after canonical workflow edits.
Run repository-required substantive-code pre-handoff gates and record any baseline
failures accurately; do not claim unexecuted suites. For this scaffold, run
`wctl doc-lint --path docs/work-packages/20261116_integration_history_governance`.

## Validation and Acceptance


The review artifacts contain the acceptance matrix. Required observable outcomes:
unpushed acceptance fails closure even when push is a valid fast-forward; ordinary
merge-preserving integration succeeds; stale/offline/shallow/incorrect-target inputs
cannot yield a successful receipt; concurrent movement follows the selected retry
contract; dirty files remain unchanged; wrong-container-checkout tests fail;
post-acceptance reverts fail the behavioral gate despite preserved ancestry; and
policy weakening cannot self-approve from candidate-owned code. Remote enforcement
must reject a nonconforming update while permitting the operator's normal workflow.

## Idempotence and Recovery


Verifiers are read-only except explicitly named temporary refs and receipt outputs.
Retries must not rewrite existing acceptance records or erase working files.
Export original rule settings and rollback instructions before remote mutations;
recovery exceptions identify actor, reason, revision, scope, and follow-up evidence.
A backup ref helps recover work but does not establish remote integration. Never
remove incident backups merely because local tests passed.

## Artifacts and Notes


Retain incident inventory, all three independent design reviews, synthesis,
ratified decisions, real-Git transcripts, exact receipt/readback examples, workflow
results, rule exports, canary outcomes, and implementation re-reviews. Keep secret
values and credentials out of artifacts. Status claims must name their evidence.

## Interfaces and Dependencies


Use Git CLI and Python standard library; wctl wraps tests. Define a versioned
receipt schema and stable failure categories before callers adopt them. GitHub
protection/rules API support, identity and reviewer availability are environment
inputs, not assumptions. No additional service or credential is authorized.

Revision note (2026-11-16): initial scaffold incorporates independent reviewers'
worktree validation and publication-boundary concerns; operator decisions remain open.

Execution amendment (2026-11-16): implement the authorized defaults; PR-only with
zero required human approvals initially, admin enforcement and no routine bypass.
Owner policy approval is exact candidate/digest configuration, not an external
message. Operational observation remains open until five real integrations occur.

Enforcement readback (2026-11-16): GitHub accepts an eligible open PR head via
fast-forward push and records it as merged. The tested contract is PR association
and required checks, not merge-button-only transport. No-PR pushes were separately
rejected with status checks removed on the disposable canary to isolate that rule.
