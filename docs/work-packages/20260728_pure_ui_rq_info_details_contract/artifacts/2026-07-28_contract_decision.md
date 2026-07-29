# Contract Decision - SURF-17 Active Jobs by Queue

**Status**: Accepted checkpoint draft; implementation conformance pending
**Date**: 2026-07-28 UTC
**Starting implementation revision**:
`bbba58359b4f45d88eab610c27cd467bb5964a3b`
**Operator approval**: The operator explicitly approved including separation of
the active job list by the default and batch queues in SURF-17 on 2026-07-28.

## Applicable Authority

- `docs/standards/contract-first-change-standard.md`
- `docs/ui-docs/controller-contract.md`
- `docs/work-packages/20260728_pure_ui_rq_info_details_contract/package.md`
- `docs/work-packages/20260728_pure_ui_rq_info_details_contract/artifacts/field_matrix.md`

The canonical controller-specific contract is the concise intent contract in
this package.

## Normative Delta

The active job presentation changes from one combined table to one panel per
requested queue. The default request renders `default` then `batch`. The
existing `queues` query parameter controls both collection and panel order.
Every panel has an explicit empty state and receives only active jobs whose
producer-supplied `queue` string, after surrounding whitespace is stripped,
equals its requested queue name case-sensitively. Requested names preserve
spelling and order after surrounding whitespace is trimmed. A repeated name is
represented by its first occurrence only.

Recently completed and failed jobs remain combined tables. The Queue column,
lookback values, Admin/Root authorization, read-only snapshot, escaping,
navigation, error behavior, and job-listing payload remain unchanged.

## Rationale

Default work and long-running batch work have different operational meaning.
Separate active panels make backlog and worker activity scannable without
adding polling or changing the underlying RQ APIs.

## Compatibility Impact

The route URL and query parameter are unchanged. Template context gains an
ordered queue-panel structure; the combined active list is an internal
presentation input and has no external API contract. Custom requested queues
remain supported. Unknown or unrequested queue values are not reassigned.

## Security Impact

Security remains high because the page displays privileged job, worker, run,
and submitter metadata. The change must not widen the Admin/Root role gate,
expose new fields, create cross-queue leakage, or add mutation. Rendered values
remain escaped and external-tab links retain `rel="noopener"`.

## Discrepancy Classification

This is an operator-approved intended presentation-contract change. It is not a
conformance repair, so production edits remain blocked until two independent
read-only reviews are dispositioned and this checkpoint is committed as a
standalone ancestor.

## Regression Evidence Plan

- Route tests prove default and custom queue order, exact grouping, explicit
  empty panels, whitespace trimming, case-sensitive differences,
  first-occurrence duplicate handling, and no unknown/unrequested cross-queue
  reassignment.
- Direct template rendering proves separate headings, job/run links, escaped
  hostile metadata, and combined recent/failed panels.
- A new focused `tests/rq/test_job_listings.py` exercises the real producer's
  payload, queue collection, and read-only behavior because existing
  admin-route tests mock that boundary.
- Authorization tests prove anonymous and ordinary authenticated users cannot
  access the surface while Admin and Root can.
- Static inspection and tests prove no forms, mutation actions, polling, or
  queue wiring changes.

## Alternatives Rejected

- Client-side filtering was rejected because server-owned grouping is simpler
  to test and avoids duplicating queue normalization in presentation code.
- Hard-coding only two tables was rejected because the existing `queues` query
  parameter supports ordered custom queue selection.
- Splitting recent and failed tables was rejected as unrelated scope.
- Adding polling was rejected because the page is explicitly a static
  privileged snapshot.

## Rollback

Restore the combined active table and remove the ordered grouping context. No
RQ state or stored data requires migration or rollback.

## Independent Review

Two independent read-only reviews passed after exact queue comparison,
duplicate, umbrella security metadata, and real-producer evidence findings were
resolved. The reviews and disposition are recorded beside this decision.
