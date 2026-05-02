# Dispatch Prompt: GO / NO-GO Readiness Review

## Objective
Review the work package for execution readiness and return a strict GO/NO-GO decision for autonomous execution of M1-M6.

## Scope
Assess only this package and its direct dependencies:
- `docs/work-packages/20260502_mofe_flagged_hillslope_triage/package.md`
- `docs/work-packages/20260502_mofe_flagged_hillslope_triage/tracker.md`
- `docs/work-packages/20260502_mofe_flagged_hillslope_triage/prompts/active/mofe_flagged_hillslope_triage_execplan.md`
- `docs/mini-work-packages/20260502_rq_replay_mofe_260501_validation/artifacts/`
- `PROJECT_TRACKER.md`

## Review Standard
Treat this as an operational launch gate. Prioritize blockers that would cause failed, ambiguous, non-reproducible, or unsafe execution.

## Required Checks
1. **Path and artifact-home correctness**
- All output paths resolve to `docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts/`.
- No stale references to mini-work-package output locations for active execution.

2. **Contract clarity and determinism**
- M1-M6 inputs, outputs, and acceptance criteria are explicit and testable.
- Taxonomy and disagreement workflow can be executed without ad hoc interpretation.

3. **Preconditions and environment gate**
- Preconditions are explicit and sufficient (`/workdir/wepp-forest`, `/wc1/runs`, python deps).
- Failure behavior is defined when preconditions are not met.

4. **Autonomous execution friction**
- Identify missing scripts/interfaces/commands that must exist before kickoff.
- Identify any unresolved ambiguity likely to cause operator back-and-forth.

5. **Tracker and lifecycle readiness**
- Work package appears in `PROJECT_TRACKER.md` and aligns with package status.
- Tracker state is sufficient for handoff continuity.

## Output Format (strict)
Return exactly these sections:

1. `Verdict: GO` or `Verdict: NO-GO`
2. `Blocking Findings` (numbered; include file path + line reference)
3. `Non-Blocking Findings` (numbered; include file path + line reference)
4. `Minimum Fix Set` (numbered, concrete edits required to reach GO)
5. `Confidence` (`high`/`medium`/`low`) with one-sentence rationale

## Decision Rule
- `GO` only if no blocking findings remain.
- Any missing execution-critical dependency, ambiguous contract, or invalid path/reference is `NO-GO`.
