# Default isolated test execution

This living ExecPlan follows docs/prompt_templates/codex_exec_plans.md.

## Purpose / Big Picture

The usual wctl pytest command should use isolated candidate execution and runtime
preflight. Ordinary pytest runs should retain fast Disturbed contract coverage
without running its 96 native simulations and dependent summaries. The native
matrix remains available through an explicit operator flag.

## Progress

- [x] Inspect existing runner and Disturbed matrix class/fixtures.
- [x] Implement alias/default registration and matrix selection policy.
- [x] Validate actual command execution and matrix collection behavior.
- [x] Finish documentation and evidence.

## Surprises & Discoveries

Disturbed's expensive matrix is marked slow/integration but currently collected
by every ordinary broad run. Its summary tests consume shared matrix results and
must follow the same opt-in policy. Lightweight contracts import matrix helpers
and must remain available. The report pins the producer source hash: an initial
class marker made it stale, so classification lives entirely in the selection
plugin. The producer and historical provenance retain their original bytes.

## Decision Log

2026-11-18, operator authority: promote isolated execution to run-pytest, preserve
an explicit run-pytest-shared escape hatch and the worktree alias. Opt out only
the native Disturbed matrix by default; no inference that all native matrices
should be disabled. Use pytest deselection rather than fake passing assertions.

## Outcomes & Retrospective

Completed locally. Default run-pytest uses the isolated runner; the legacy shared
path is explicit. Validation passes 113 tests with 99 native matrix items
deselected. Actual collection restores all 115 Disturbed items with the opt-in
and preserves all 516 Roads cases. No native simulation was run for this policy
change. Producer source and historical provenance remain byte-identical. Broad
preflight remains blocked on known prerequisites, not falsely marked passed.

## Work and acceptance

Change tools/wctl2 command registration, add tests/pytest_selection.py through
root conftest's pytest plugin registration, and classify the exact native matrix module during collection. Keep its source-pinned implementation unchanged.
Test real temporary pytest sessions with a marked sentinel to prove default
non-execution and flag-enabled execution. Collect the real Disturbed suite in
both modes and compare node inventories; run its lightweight default suite.
Do not run the actual 96-case simulation matrix for this selection-only change.
Exercise wctl run-pytest as the new default and retain the existing shared and
sharded command tests. Update README, test onboarding and current matrix usage.
Broad execution remains subject to the known schema prerequisite; report blocked
preflight honestly rather than requiring unrelated migrations for this change.
