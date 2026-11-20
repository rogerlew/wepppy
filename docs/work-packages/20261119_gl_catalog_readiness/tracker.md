# GL catalog readiness tracker

## Progress

- [x] 2026-11-20 00:40 UTC. Scaffolded the package, draft decision, scoped test matrix and execution plan.
- [x] Approved for execution by the operator. Two reviewers accepted the amended contract. See [review dispositions](artifacts/20261120_contract_review_disposition.md).
- [ ] Commit canonical amendments and the approved checkpoint as the standalone ancestor. Record its SHA here.
- [ ] Add and run scoped server, admission, client and browser tests.
- [ ] Verify real publication and both dashboards against the same result fixture. Retain correctness and security review artifacts.

## Decisions

- **2026-11-20 00:40 UTC.** Use a readiness handshake before GL query fan-out and a pending response for late invalidation. The operator requested the user-visible handshake. The wire and failure matrix remain draft.
- **2026-11-20 00:40 UTC.** Reuse current catalog workers and scheduler. Keep work isolated on `task/gl-catalog-readiness`, based on the available `origin/master` revision.

## Handoff

The active plan is [implementation_execplan.md](prompts/active/implementation_execplan.md). Work is at scaffolding. Runtime implementation, executable tests, contract-review approval, the checkpoint commit, and deployment evidence are pending.
