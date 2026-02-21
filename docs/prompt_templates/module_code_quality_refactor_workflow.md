> Module Code Quality Refactor Workflow (Multi-Agent, Closure Required)

Background references:
- `AGENTS.md` -> core directives, scope discipline, validation entry points
- nearest subsystem `AGENTS.md` for the touched module path
- `code-quality-summary.md` (or current observability output) for hotspot triage
- `tests/AGENTS.md` for test and stub expectations

Use this workflow when a module has code-quality hotspots (size, complexity, readability, exception-shape drift) and you need a behavior-preserving refactor that finishes to closure, not a partial pass.

## Hard Rule: Closure Required

Do not stop at "refactor drafted" or "core changes done". The task is complete only when:
- implementation is merged in working tree,
- required validations are green,
- reviewer findings are resolved (or explicitly accepted with rationale),
- handoff summary includes commands run, outcomes, and residual risks.

## Goal

Improve code quality in one bounded module while preserving runtime behavior and existing contracts.

Quality refactor means:
- smaller and clearer functions,
- reduced cognitive complexity where practical,
- narrower and explicit exception handling,
- no speculative abstractions or hidden fallback behavior.

## Scope Controls

- Pick one module and one bounded responsibility cluster per pass.
- Preserve API signatures, payload contracts, queue wiring semantics, and file formats unless explicitly requested otherwise.
- Prefer extraction/decomposition over logic rewrites.
- Avoid unrelated churn in adjacent files.

## Multi-Agent Execution Flow

1. Explorer pass (read-only mapping)
   - Map hotspots, function boundaries, and low-risk extraction points.
   - Propose one bounded refactor target and expected tests.
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

5. Closure pass (required)
   - Resolve reviewer findings for this scope (or document explicit acceptance).
   - Re-run impacted validations.
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
```

If `.pyi` or stub-exposed API changed:
```bash
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

## Acceptance Criteria

- Behavior and contracts preserved for in-scope functionality.
- Refactor scope is bounded and reversible.
- Required validations completed and green.
- Reviewer reports no unresolved high-severity findings.
- Closure summary includes:
  - files changed,
  - commands executed,
  - test outcomes,
  - residual risk statement.

## Copy/Paste Prompt Skeleton

```text
Pilot a code-quality refactor on <module_path>.

Workflow:
1) Spawn explorer to map hotspots, function boundaries, and likely low-risk extraction points.
2) Spawn code_quality_refactorer to apply a minimal behavior-preserving refactor for one bounded area.
3) Spawn test_guardian to propose and run targeted regression tests.
4) Spawn reviewer to assess correctness/regression risk.
5) Complete closure: resolve findings, rerun impacted validations, and provide final closure summary.

Constraints:
- Preserve runtime behavior and API contracts.
- Keep change scope tight and reversible.
- Use wctl-based validations relevant to touched code.
- Do not stop before closure criteria are met.
```
