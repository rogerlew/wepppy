# Parquet CSV CLI tracker

**Started / updated**: 2026-11-18 18:13 UTC
**Phase**: Scaffold complete; contract discovery next
**Security impact**: high; dedicated review required during execution
**Active plan**: [implementation_execplan.md](prompts/active/implementation_execplan.md)

## Task board

- [x] Scaffold brief, standalone contract draft, decision checkpoint and ExecPlan.
- [x] Register package on PROJECT_TRACKER.md in the isolated task worktree.
- [ ] M0: Inventory compatibility and dependencies; ratify contract and resource ADR.
- [ ] M0: Two independent contract reviews; retain checkpoint ancestor SHA.
- [ ] M1: Implement isolated Rust CLI and generated-output parity tests.
- [ ] M2: Implement standalone async Python harness and bounded lifecycle tests.
- [ ] M3: Run representative three-way performance and resource evaluation.
- [ ] M4: Complete correctness/security reviews and go/no-go handoff.

## Decisions

- 2026-11-18: Contract-first and standalone-first per operator. Integration is
  outside this package even after success; a successor requires separate authority.
- 2026-11-18: Evaluate Rust; compare current exporter and native incremental
  PyArrow. No claimed speedup, fixed resource defaults or dependency approval yet.
- 2026-11-18: Worktree `/home/workdir/wepppy-parquet-csv-cli-package`, branch
  `codex/parquet-csv-cli-package`; shared checkout has unrelated WIP and is untouched.

## Gate status and evidence

Contract approval: pending. Checkpoint ancestor: none. Implementation: not started.
Correctness/security review artifacts: not yet produced; use canonical templates.
Performance and resource acceptance: not measured. WEPPpy integration: deferred.
Publication/deployment: outside scope. Scaffold docs validation: passed (six files, zero errors/warnings); staged diff whitespace check passed. Spelling preview reviewed; retained the ordinary word "oversized".

## Risks and next action

Resolve CSV serialization differences and codec coverage before selecting crates.
Do not confuse row batching with bounded allocation, task cancellation with process
termination, or per-worker admission with an aggregate service limit. Retain
whole-tree resource evidence and ensure legitimate large exports remain supported.

Next action on authorized execution: M0 of the active plan. Do not implement from
this unratified draft. Review [checkpoint](artifacts/20261118_contract_decision.md)
and [package scope](package.md#scope-and-integration-boundary) first.

## Validation note - 2026-11-18 18:18 UTC

The installed wctl wrapper selects its installation checkout even when called
from a task worktree. Initial relative-path lint calls validated zero new files;
staging was not the cause. Explicit `wctl --project-dir
/home/workdir/wepppy-parquet-csv-cli-package doc-lint --path ...` validated all
six changed documents. Use this override for reproducible worktree doc checks.
No runtime tests were run for this documentation-only scaffold.
