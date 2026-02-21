> Module Code Quality Refactor Workflow (Multi-Agent, Compliance Closure Required)

Background references:
- `AGENTS.md` -> core directives, scope discipline, validation entry points
- nearest subsystem `AGENTS.md` for the touched module path
- current observability outputs (`code-quality-summary.md` CI artifact/comment, or local `/tmp` output) for hotspot triage
- `docs/dev-notes/code-quality-observability.md` for severity bands and interpretation
- `tests/AGENTS.md` for test and stub expectations

Use this workflow when a module has code-quality hotspots (size, complexity, readability, exception-shape drift) and you need a behavior-preserving refactor that reaches code-quality compliance closure, not a partial pass.

## Hard Rule: Compliance Closure Required

Do not stop at "refactor drafted" or "core changes done". The task is complete only when:
- implementation is complete in the working tree and ready for review/commit,
- target module and any files spun out from it are compliant with repo code quality guidelines,
- target module and any spun-out files are not in `red` severity bands for tracked observability metrics, unless an explicit human-approved maintainability exception is recorded,
- required validations are green,
- reviewer findings are resolved (or explicitly accepted with rationale),
- relevant documentation is updated for the refactor outcome,
- observability evidence is captured (CI report or local temporary outputs),
- handoff summary includes commands run, outcomes, and residual risks.

If additional reduction would materially harm maintainability or legibility, document a senior-developer-level rationale (tradeoff, evidence, and explicit residual debt) and obtain explicit human approval for a maintainability exception before closure.

## Goal

Bring one bounded module (and any extracted files created during the refactor) into practical compliance with repo code quality guidelines while preserving runtime behavior and existing contracts.

## Compliance Rubric (Required)

Treat compliance as measurable, not qualitative-only. At closure, provide explicit before/after evidence for in-scope files.

- Changed-file rule: no in-scope changed file should be reported as `worsened` for tracked observability metrics (`python_file_sloc`, `python_function_len`, `python_cc`, `js_file_sloc`, `js_cc`). Any numeric worsening (including same-band changes) requires documented rationale and an approved maintainability exception.
- Target-module rule: the target module should improve at least one hotspot dimension (for example max function length, max complexity, or decomposition into clearer responsibility boundaries).
- Red-zone exit rule: at closure, the target module and any spun-out files must be below `red` severity for tracked observability metrics. If any in-scope file remains `red`, closure is blocked unless a human reviewer/owner explicitly approves a maintainability exception.
- No-regression rule: runtime behavior and contract tests for impacted scope remain green.
- Exception-shape rule: do not introduce broad catches (`except Exception`, bare `except`) unless the block is a deliberate boundary and rationale is documented.
- Historical-exception rule: when a selected refactor responsibility cluster contains existing broad catches, narrow or eliminate those catches in the touched scope when practical. Any remaining broad catch in touched scope must be documented as a deliberate boundary with explicit rationale.
- Exception-approval rule: maintainability exceptions may be proposed by the agent, but must be explicitly approved by a human reviewer/owner before closure.
- Documentation rule: update docs for moved responsibilities, new collaborator boundaries, and any changed operational commands.

Quality refactor means:
- smaller and clearer functions,
- reduced cognitive complexity where practical,
- narrower and explicit exception handling,
- no speculative abstractions or hidden fallback behavior,
- no "gaming" metrics that degrades readability or maintainability.

## Scope Controls

- Pick one module and one bounded responsibility cluster per pass.
- Preserve API signatures, payload contracts, queue wiring semantics, and file formats unless explicitly requested otherwise.
- Prefer extraction/decomposition over logic rewrites.
- Treat newly extracted files as in-scope for compliance and review.
- Avoid unrelated churn in adjacent files.

## Baseline Capture (Required Before Edits)

Before making code changes, capture baseline observability evidence for the target module/hotspots.

- Preferred: use the latest CI `Code Quality Observability` output (`code-quality-summary.md` artifact or PR comment).
- Local fallback (temporary outputs only):
```bash
python3 tools/code_quality_observability.py \
  --base-ref origin/master \
  --md-out /tmp/code-quality-summary.pre.md \
  --json-out /tmp/code-quality-report.pre.json
```
- Record the target file's starting metrics in milestone notes so closure can provide explicit before/after evidence.

## ExecPlan Gate (Required for Complex Refactors)

Apply ExecPlan discipline before implementation when the refactor is significant, multi-cycle, or multi-hour.

- Required trigger: create or adopt an active ExecPlan before code edits when the pass is expected to need multiple milestones, cross-subsystem coordination, or more than about two hours of work.
- Default plan location: `docs/work-packages/*/prompts/active/`.
- Mini-work-package location: `docs/mini-work-packages/*.md` only when explicitly designated.
- Before authoring/revising a plan, read `docs/prompt_templates/codex_exec_plans.md`.
- During each milestone cycle, keep ExecPlan sections current: `Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`.
- If the active plan is under `docs/work-packages/*/prompts/active/`, update the paired `docs/work-packages/*/tracker.md` during milestone progression and at closure.
- Final closure must record validation outcomes, compliance outcome (or approved exception), and observability evidence references in the active ExecPlan.

## Fast Path (Small Bounded Passes)

Use fast path when all are true:
- one module and one responsibility cluster;
- likely one milestone cycle;
- no cross-subsystem contract, queue wiring, or file-format changes;
- expected completion in about two hours or less.

ExecPlan is optional in fast path, but closure requirements still apply: baseline and post-refactor observability evidence, relevant validation gates, reviewer pass, and closure summary.

## Spun-Out Files Checklist (Required When Splitting Code)

For each newly extracted file:

- verify imports, exports, and call-site wiring;
- for Python extractions, preserve type/API surface (`.pyi`, `__all__`, and public contracts where applicable);
- for JavaScript extractions, preserve export surface and call-site contract parity;
- add or update focused regression coverage for the extracted responsibility;
- update nearby docs pointers (README/AGENTS/work package notes) when ownership boundaries change;
- include spun-out files in milestone quality evidence and final closure notes.

## Iteration Model (Milestones + WIP Commits)

Complex modules can require multiple cycles. Run milestone-to-milestone until compliance closure is reached.

- Each cycle should end with a milestone checkpoint: what changed, quality impact, validation status, and open risks.
- When an ExecPlan is active, each milestone checkpoint must update the plan before continuing.
- If commits are part of the working agreement, WIP commits are allowed and encouraged for long-running refactors to preserve reversibility and reviewability.
- Suggested WIP commit format:
  - subject: `wip(<module_or_area>): <milestone_label>`
  - body: scope completed, quality delta snapshot, validations run, remaining hotspots, next milestone.
- Do not declare done mid-cycle; continue until closure criteria are met or an explicit maintainability exception is documented.
- Stop condition (explicit): stop cycling when either:
  - compliance rubric is satisfied, validations are green, and the target module/spun-out files are not `red`; or
  - further metric reduction is net-negative for maintainability/legibility and a human reviewer/owner explicitly approves a documented maintainability exception.

## Multi-Agent Execution Flow (Per Cycle)

1. Explorer pass (read-only mapping)
   - Map hotspots, function boundaries, and low-risk extraction points.
   - Flag historical broad catches in the selected responsibility cluster and propose which ones will be resolved this cycle.
   - Propose one bounded refactor target, expected tests, and expected quality delta.
   - Output: concrete plan with file paths and risk notes.

2. Refactorer pass (implementation)
   - Apply the minimal behavior-preserving refactor for the selected target.
   - Keep changes reversible and localized.
   - Output: diff summary and any risk flags.

3. Test guardian pass (validation)
   - Run focused regression tests first.
   - Add subsystem gates only when applicable (see Validation section).
   - Output: exact commands, pass/fail counts, and uncovered risk gaps.

4. Reviewer pass (risk assessment)
   - Review the exact diff and test evidence.
   - Prioritize findings by severity with file:line references.
   - Output: findings, assumptions, residual risk, accept/rework recommendation.

5. Milestone decision
   - Resolve reviewer findings for this cycle (or document explicit acceptance).
   - Decide whether another cycle is required for compliance closure.
   - If more work remains, capture checkpoint notes and continue with the next cycle.

6. Closure pass (required, final cycle only)
   - Confirm module + spun-out files are compliant, or document approved maintainability exception.
   - Confirm target module + spun-out files are not `red` on tracked observability metrics, or record explicit human-approved maintainability exception.
   - Confirm historical broad catches in touched scope were narrowed/removed, or record explicit deliberate-boundary rationale with human approval.
   - Re-run impacted validations.
   - Update relevant docs.
   - Capture observability evidence for post-refactor comparison (CI output or local temporary run).
   - Publish closure summary with outcomes and residual risks.

## Validation Gates

Start with targeted tests, then add only relevant gates for touched areas.

Core:
```bash
wctl run-pytest tests/<targeted_path_or_nodeid>
```

If RQ enqueue wiring changed:
```bash
wctl check-rq-graph
# if drift is reported:
python tools/check_rq_dependency_graph.py --write
wctl check-rq-graph
```
Update `wepppy/rq/job-dependencies-catalog.md` when enqueue dependency edges change.

If `.pyi` or stub-exposed API changed:
```bash
wctl run-stubtest <module_path>
wctl check-test-stubs
```

If frontend/controller JS changed:
```bash
wctl run-npm lint
wctl run-npm test
```

Pre-handoff sanity (recommended for non-trivial refactors):
```bash
wctl run-pytest tests --maxfail=1
```

Observability evidence at final closure (required):
- Preferred: reference CI `Code Quality Observability` output (`code-quality-summary.md` artifact or PR comment).
- Local fallback (temporary outputs only):
```bash
python3 tools/code_quality_observability.py \
  --base-ref origin/master \
  --md-out /tmp/code-quality-summary.post.md \
  --json-out /tmp/code-quality-report.post.json
```

If docs were updated:
```bash
wctl doc-lint --path <doc_path>
```

## Maintainability Exception Template (When Needed)

Agents may propose maintainability exceptions, but a human reviewer/owner must explicitly approve each exception before closure. Every approved exception must be reported in closure notes.

Use this format when compliance cannot be fully achieved without harming legibility/maintainability:

- Context: module, hotspot, and attempted refactor cycles.
- Evidence: metric deltas, reviewer/test evidence, and where readability degraded.
- Tradeoff decision: why further reduction is net-negative.
- Alternatives considered: options tried/rejected and why.
- Human approval: approver, where it was recorded, and date/time.
- Observability annotation: whether an entry was added/updated in `.code-quality-observability-exceptions.json`.
- Residual debt: exact remaining hotspot(s), owner, and revisit trigger/date.

## Acceptance Criteria

- Behavior and contracts preserved for in-scope functionality.
- Refactor scope is bounded and reversible.
- Compliance rubric satisfied with explicit evidence, or approved maintainability exception recorded using the template above.
- Target module and spun-out files meet repo code-quality guidance, or have a documented maintainability/legibility exception with rationale.
- Target module and spun-out files are not `red` for tracked observability metrics at closure, or an explicit human-approved maintainability exception is recorded.
- Required validations completed and green.
- Reviewer reports no unresolved high-severity findings.
- Relevant docs updated to reflect new structure, responsibilities, and follow-up notes.
- Observability evidence is captured and referenced (CI report preferred; local temporary outputs allowed).
- Any maintainability exception is explicitly approved by a human reviewer/owner and documented in closure notes.
- If ExecPlan gate was triggered, active ExecPlan (and tracker when required) updated through closure.
- Closure summary includes:
  - files changed,
  - commands executed,
  - test outcomes,
  - quality/compliance outcome,
  - residual risk statement.

## Copy/Paste Prompt Skeleton

```text
Pilot a code-quality refactor on <module_path>.

Workflow:
0) If the pass is expected to need multiple milestones, cross-subsystem coordination, or more than about two hours, activate an ExecPlan (work-package or explicitly designated mini-work-package) and keep it updated throughout.
1) Run cycle-based refactor milestones until compliance closure:
   - Spawn explorer to map hotspots, function boundaries, and likely low-risk extraction points.
   - Spawn code_quality_refactorer to apply a minimal behavior-preserving refactor for one bounded area.
   - Spawn test_guardian to propose and run targeted regression tests.
   - Spawn reviewer to assess correctness/regression risk.
   - Resolve findings, checkpoint milestone status, and continue until stop condition is met.
2) Final closure:
   - Confirm module + spun-out files satisfy the compliance rubric and are not `red`, or document approved maintainability/legibility exception.
   - Re-run impacted validations.
   - Update relevant documentation.
   - Capture observability evidence from CI report (or local temporary outputs in `/tmp` when CI evidence is unavailable).
   - If a maintainability exception is used, record rationale and obtain explicit human reviewer/owner approval before closure.
   - Provide closure summary with quality/compliance outcome and residual risk.

Constraints:
- Preserve runtime behavior and API contracts.
- Keep change scope tight, reversible, and milestone-driven.
- Use wctl-based validations relevant to touched code.
- Do not close while the target module or spun-out files remain in `red` severity for tracked metrics, unless there is explicit human-approved maintainability exception.
- Do not accept changed-file `worsened` metrics without explicit human-approved maintainability exception.
- Resolve historical broad catches in the selected refactor scope, or document deliberate-boundary rationale and obtain explicit human approval before closure.
- Use senior-developer judgment when further metric reduction harms maintainability/legibility.
- Do not stop before closure criteria are met.
```
