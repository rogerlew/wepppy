# Batch partial-success tracker

Updated: 2026-11-16, M1 execution in progress.

## Progress

- [x] Scaffold package, draft decision, ExecPlan, and migration guidance.
- [x] Inventory both workflows, consumers and contracts; see artifacts/20261116_inventory.md.
- [ ] Identify the separate mixed-success timeout incident; no identity is claimed.
- [ ] Amend canonical contracts; obtain approval, two independent reviews, disposition, and standalone checkpoint commit.
- [ ] Implement outcome publication and polling for both workflows.
- [ ] Verify client adoption and success-only result filtering.
- [ ] Complete artifact acceptance, regressions, correctness/security reviews, and handoff.

## Decisions and handoff

2026-11-16 06:13 UTC: Preserve RQ status and exceptions; add finalizer-owned `batch` outcome to jobinfo and jobstatus. Changing only the finalizer cannot fix aggregate-status client aborts.

Base revision: `df8b5249c70a3d98fd27f2b3b3b16ac1d96deb52`. Existing user changes include `PROJECT_TRACKER.md` and `docs/schemas/rq-response-contract.md`; preserve them. No runtime change, contract ratification, commit, deployment, or requeue is claimed. Next: M1 in `prompts/active/implementation_execplan.md`.

## M1 execution evidence

Concrete proposed canonical contract: `docs/schemas/batch-outcome-contract.md`.
The response, webhook and batch task boundary contracts cross-link the proposal.
Exact operator ratification and standalone checkpoint are pending. Runtime files
have not been edited. The external Culvert checkout is available but adoption
has not begun; its unrelated dirty files are preserved.

The proposal resolves ordinary delivery as an attempt-specific baseline WEPP ZIP
and preserves existing WATAR/Omni project downloads and legacy diagnostic ZIPs.
Prep-only selections are explicit no-result skips. Reviews additionally require
leaf retention through long timeouts, blocked Omni reconciliation, pinned client
download origins and member-level archive disclosure checks.

Independent correctness and security reviews pass the proposal at SHA-256
`42d00a1931ea77e862412349ff91414bfae47d3dc33dd57faf0eb6ac7f8fed92`;
see `artifacts/20261116_contract_correctness_review.md` and
`artifacts/20261116_contract_security_review.md` for findings and disposition.
No unresolved medium/high technical contract findings. Exact operator
ratification and standalone ancestor remain the M1 gate.

Validation: scoped `wctl doc-lint` passed package and all amended schema/guide/board
files with zero warnings/errors; `git diff --check` passed. `uk2us` previews
for the schema/package files produced no changes. No runtime tests were run
because implementation is gated and runtime source remains unchanged.

Operator approval (2026-11-16 06:31 UTC): “i approve. proceed with commit and implementation”. This ratifies the reviewed contract (pre-status-update SHA-256 `42d00a1931ea77e862412349ff91414bfae47d3dc33dd57faf0eb6ac7f8fed92`) and authorizes the standalone checkpoint and implementation commits. Runtime conformance remains pending.
