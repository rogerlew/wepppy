# Unrutted partial-crossing tracker

**Updated:** 2026-11-17 17:45 UTC
**Status:** Contract design prepared; formula approval and checkpoint pending. Implementation not started.
**Branch:** `work/roads-unrutted-strip-contract`
**Worktree:** `/tmp/wepppy-roads-unrutted-strip-contract`

## Task board

- [x] Capture agreed scope, rationale, incident observations, and test boundary.
- [x] Create package, draft decision, acceptance matrix, and active ExecPlan.
- [ ] Resolve formulas, feasibility policy, existing limits, and compatibility.
- [ ] Amend current contracts and draft parameterization ADR.
- [ ] Record exact ratification, two independent reviews and dispositions.
- [ ] Commit standalone checkpoint ancestor; record SHA here before code edits.
- [ ] Implement changed Roads paths and scoped regressions.
- [ ] Validate native artifacts and disposable 141/42 cases.
- [ ] Complete independent correctness/security reviews and user/operator docs.

## Decisions

2026-11-17 17:45 UTC — Roger endorsed a simplified strip abstraction, replacement
of 60%, exact total hillslope-area accounting, road-area preservation where
feasible, and explicit exclusion of switchback connectivity/flowpath walking.
Full drainage partitioning is intentionally deferred. Exact policy remains pending.

2026-11-17 17:45 UTC — Roger limited tests to implementation changes. Scoped
regressions and direct changed-artifact evidence replace broad suite requirements
for this package; do not add unrelated validation gates.

## Risks and unresolved questions

Road area and positive OFE lengths may conflict with hillslope closure. Width
allocation can conserve area while misrepresenting physical connectivity. Existing
parity transform, 10 m minima, and three-crossing cap need explicit disposition.
Required fill/buffer inputs remain a separate operational blocker. See the
[decision draft](artifacts/20261117_contract_decision.md).

## Validation and completion ledger

Documentation lint: all six package files and PROJECT_TRACKER.md passed with zero
errors/warnings using `markdown-doc lint` in the task worktree. Relative-link
readback and uk2us preview passed. The installed `wctl doc-lint` wrapper resolved
the shared checkout (zero task files); absolute worktree paths triggered an
ignore-library panic. Direct canonical linter execution validated the actual files.
Tooling follow-up: make doc wrappers honor the selected worktree like test wrappers.
Contract reviews: two performed; A and B passed after fixes; no remaining medium/high findings.
Checkpoint SHA: none. Code: not changed.
Native acceptance: not run. Integration/publication/deployment/repair: not performed.
No production action is authorized by the scaffold.

## Handoff

Next: capture pending formula approval and final review disposition, then commit
the checkpoint before implementing. Use [active ExecPlan](prompts/active/implementation_execplan.md); all future
production changes require the accepted ancestor checkpoint. Keep this tracker and
the plan's living sections current. Preserve unrelated shared-checkout WIP.

## Execution authorization — 2026-11-17

Roger instructed “proceed” and authorized mutation/forking of the synced forest
run. M1 is active. Proposed formula contract and ADR-0146 are prepared for review;
exact formula approval is pending the asynchronous question. Local host is forest;
`/wc1/runs/mi/misty-eyed-divorcee` exists. Prefer a disposable fork.

Final M1 preparation: canonical draft and ADR-0146 written; both reviews pass.
All package Markdown passes lint; ADR date gate passes. Exact formula approval
remains pending, so checkpoint commit and implementation have not started.

## Ratification — 2026-11-17 UTC

Roger approved the concrete geometry rule and instructed implementation. Both
reviews pass. Checkpoint is accepted; implementation begins only after its commit.
