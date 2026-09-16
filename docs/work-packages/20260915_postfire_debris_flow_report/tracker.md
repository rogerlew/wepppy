# Tracker — Post-fire debris-flow report

Started: 2026-09-15 21:44 UTC. Closed: 2026-09-15 21:56 UTC.
Current phase: documentation delivered; report implementation pending.
Security impact: low (docs + read-only role registration); security review passed.
Starting revision: `e6c821cdd844e1cde360bd76d3ce500f389b3f15`.
Contract ancestor: none; no implementation authorized or performed.

## Task board

- [x] Inspect report precedents and scientific/data contracts.
- [x] Draft proposed report contract and conservative first-release boundary.
- [x] Link module specification and roadmap.
- [x] Create implementation plan, field/state matrix and decision record.
- [x] Independent correctness, security and dedicated UX review; all findings resolved and confirmed.
- [x] Validate docs/configuration and close documentation scope.

## Decisions

2026-09-15 21:44 UTC — Separate durable report behavior from execution history.
Use one duration selector and persisted results first; defer maps, continuous
curves and custom targets. This reduces unratified semantics and controls while
preserving the primary rainfall-likelihood question. These are proposed UX choices.

## Risks and handoff

An accepted model is not the current selector value. Date labels are not always
calendar dates. Event rows contain repeated durations. Coverage is not confidence.
Each is covered by the contract and acceptance matrix. All new presentation
choices remain pending owner ratification; implementation needs its own checkpoint.

## Validation

Targeted Markdown lint, spelling preview, cross-reference/diff checks and TOML
parse/role-registration checks passed; [evidence](artifacts/validation.md).
No runtime tests or live reruns performed for documentation/role changes.
Unrelated dirty code-quality report files remain untouched.

## Final handoff

2026-09-15 21:56 UTC — All three reviewers confirmed amendments resolved.
[Disposition](artifacts/review_disposition.md) and separate review artifacts are
retained. The requested UX role is registered without permission/model changes;
this session's UX review ran with the explicit retained brief.

Next phase: owner ratification of the proposed report scope, exact adapter
contracts and a reviewed standalone ancestor checkpoint before implementation.
The [implementation plan](artifacts/implementation_plan.md) records that work;
this package closes documentation only, not roadmap stage 7 delivery.
