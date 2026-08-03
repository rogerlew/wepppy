# WEPP workflow single-flight contract decision

**Decision date**: 2026-08-03 UTC
**Decision owner/operator**: User requesting the production incident fix
**Implementer**: Codex
**Starting revision**: `9a02c00f2700afdd4150e0e3bf760b6f530ff54f`
**Security impact**: Low; no authentication or authorization boundary changes

## Problem and observed evidence

The existing per-run submit mutex covers only the route's check-and-enqueue transaction. The recorded orchestration root then finishes after constructing its child graph, so later requests can see that root as terminal while its hillslope or watershed children remain active. Production showed two `_run_hillslopes_rq` children for `compositional-disorganization` overlapping on separate workers after two no-prep roots were accepted.

The pinned RQ 1.16.2 API also returns `JobStatus` enum values and byte dependency keys. The contract therefore requires explicit normalization rather than relying on string-shaped test doubles.

## Accepted normative behavior

All five keys in `WEPP_RQ_JOB_KEYS` participate in one per-run single-flight admission check. A recorded root or linked descendant in queued, started, or scheduled state blocks another submission. A deferred descendant blocks only when its own transitive dependency chain remains viable. If that chain contains a failed, stopped, or canceled dependency, that deferred descendant cannot execute and does not block retry. An unrelated failure does not invalidate another viable or executable branch. Missing dependency records are ambiguous and remain conservatively blocking.

The existing HTTP 409 conflict response, route submit mutex, status receipt, cancellation tree, enqueue edges, and authorization rules remain unchanged.

## Alternatives rejected

- Holding a new Redis lock for the complete workflow was rejected because every descendant failure/cancellation path would need reliable ownership-safe release.
- Tracking only the final deferred job was rejected as the sole design because upstream failures can strand that job; dependency-aware interpretation is still required.
- Treating every deferred job as active forever was rejected because it prevents legitimate recovery after failed workflows.

## Operator approval

The operator explicitly requested the fix, required watershed tracking verification, and required dual-agent review on 2026-08-03. This approval covers the behavior above: prevent overlapping same-run WEPP workflows across normal and watershed paths while retaining recoverability after terminal dependency failure.

## Independent contract reviews

- **Correctness reviewer**: Approved the substantive contract after byte-key and per-dependency corrections. The seven-day receipt-retention edge was classified as residual rather than incident-path blocking.
- **QA reviewer**: Accepted the substantive wording and required exact revision provenance, saved review artifacts, and this documentation-only ancestor commit before implementation proceeds.

Detailed findings and dispositions are recorded in `20260803_contract_code_review.md` and `20260803_contract_qa_review.md` beside this decision.
