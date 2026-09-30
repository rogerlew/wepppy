# Catalog projection contract checkpoint

**Status**: Accepted for implementation; independent contract reviews PASS.
Operator execution authorization: 2026-09-30 UTC, following review commit
`442aa56d2`: execute this package and hold when ready to deploy to forest.
This approves the reviewed behavior and initial limits for implementation and
validation, not measured capacity claims or deployment. No live migration,
service restart, sweep activation, or read-mode cutover is authorized.
**Date**: 2026-09-30 UTC.
**Starting implementation revision**: `c8497e2cbf210ebc74ef51e2c73cb5351373da2f`.

## Operator-established intent

Projects remain usable outside a deployment without PostgreSQL. The operator
endorsed a rebuildable catalog beside registration records and requested a full
specification with implementation and rollout through forest, forest1, then
wepp1. The current task authorizes documentation, not runtime edits/deployment.
Do not represent this as approval of every newly specified numeric default or
as the required independent contract reviews.

## Current authorities and changes

| Authority | Intended delta |
| --- | --- |
| `docs/schemas/run-catalog-projection-contract.md` | Complete table, portable observer, reconciliation, read/UI modes, gates, rollout |
| `docs/schemas/nodb-persistence-concurrency-contract.md` | Explicit optional post-commit integration replaces direct web dependency; durable file authority unchanged |
| `docs/ui-docs/contracts/runs-catalog-ttl-deletion-contract.md` | SQL projection as read source after cutover; freshness-dependent TTL suppression; policy/deletion authority unchanged |
| `docs/adrs/ADR-0078-run-catalog-projection.md` | Architecture rationale and proposed workflow limits |
| `docs/schemas/rq-response-contract.md` | Catalog-only identifier exception and bounded job-info/jobstatus disclosure, including outer failures and retained-record rollback; unrelated polling preserved |
| `docs/schemas/weppcloud-csrf-contract.md` | Preserve existing session/mutation protection; no new browser mutation endpoint |
| `docs/schemas/run-sync-contract.md` | Preserve transfer success/provenance order; catalog notification only after completed source publication |
| `docs/standards/contract-first-change-standard.md` | Reviews and accepted contract ancestor before runtime implementation |

This is an intentional performance architecture and presentation change, not
merely restoration of an existing implementation. Existing filesystem reads
are evidence of current behavior, not a prohibition on the proposed projection.

## Compatibility and regression plan

Add one deployment table and additive freshness payload fields. Preserve run
IDs, names/scenario semantics, owner/ACL joins, sorting/pagination, URLs, file
formats, NoDb locks, TTL policy and physical deletion authority. No scientific
defaults or generated WEPP parameters change. Authoritative project state must
remain byte-compatible through save/archive/restore and standalone operations.

Explicit user-visible deltas: short pending period for new records; labeled
last-good rows during transient errors; known-dirty/old TTL suppression; no
automatic NFS fallback during database outages. These detailed policies and
operating limits require explicit disposition at ratification.

Validate real file→SQL→HTTP→browser propagation, legacy extraction, omissions,
all writer processes, standalone imports, SQL outages/races, missed/offline
updates, scheduler coalescing, restart/rebuild/deletion fencing, authorization,
and production-equivalent host identities/mounts. Retain semantic readback and
latency evidence, not only row/job counts.

## Review and commit gate

Independent contract reviewer 1: Dirac; final contract-only PASS, COR-01 through COR-05 closed.
Independent contract reviewer 2: Ohm; final contract-only PASS, SEC-01 through SEC-05 closed.
Detailed operator ratification/disposition: execution authorized on 2026-09-30 UTC.
Correctness/security initial verdicts: HOLD; post-fix verdicts: PASS. No risk acceptance.
See [review disposition](2026-09-30_contract_review_disposition.md) for all
findings, changes, and supplemental OPS-01 closure.
Specification commit: `62d4273d9`, authorized by the operator's prior commit request.
Reviewed contract ancestor: `442aa56d2`; the acceptance-record commit immediately
following it completes the pre-implementation checkpoint. Record that commit's
SHA in the tracker before runtime edits.

Once reviews and detailed disposition are complete and committing is authorized,
commit this specification/ADR/shared-contract set separately, then record its
SHA here and in the tracker. Runtime commits must descend from that checkpoint.
