# Comrak Markdown migration tracker

## Progress

- [x] Inventory cmarkgfm call sites and compare available bindings.
- [x] Review and commit the contract checkpoint at `4d9d7416b`.
- [x] Implement the shared adapter and migrate production and build consumers.
- [x] Validate rendered output and the native dependency in the local candidate runtime.

## Decisions

The feature branch is `task/comrak-markdown-migration`. It starts at the
Usersum vendor graph implementation `547ada295`. Select `comrak-ext`
because its published wheel exposes the syntax tree and embeds Comrak 0.59.0.
See the [contract decision](artifacts/20261120_contract_decision.md).

The [correctness review](artifacts/20261120_correctness_review.md) and
[security review](artifacts/20261120_security_review.md) record 363 passing
focused tests and the AST resource-retention fix. The focused image
contains the pinned wheel with the old dependency removed. The unrestricted run was stopped in the unrelated Disturbed soil
artifact matrix. The repository-wide run excluding slow-marked tests
passed with 14,033 passes, 338 skips and 1,093 deselections. The worktree
validation receipt is `.wctl-test-runs/0e47c859c2164e6c93abdef9b2d14b05/receipt.json`.
Integration and deployment were outside this local validation run.
