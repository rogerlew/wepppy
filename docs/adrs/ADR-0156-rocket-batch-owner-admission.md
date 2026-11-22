# ADR-0156: Temporary Rocket batch-owner admission cap

Status: Accepted

Date: 2026-11-21

## Decision and provenance

The production operator and Codex selected an opt-in limit of two outstanding
refresh reservations per batch guard owner for the Rocket deployment during the
November 21 query catalog study. Previously only global capacity limited siblings.
The policy defaults off.

## Rationale and evidence

Seven siblings compete for the same filesystem guard. In the production-offset
trials, median occupied worker time fell from 24.3 to 15.9 worker-seconds with
two admitted siblings. Only two of four batch completion comparisons improved.
All 224 timed receipts passed catalog readback. The study is retained under
`/wc1/query-catalog-validation/batch-owner-qh05IUvH/evidence`.
Worker-side retry lacked evidence of an advantage. Admission can preserve an
available worker for other projects without changing the lock protocol.

## Consequences and rollback

Long children can increase a batch's completion time. Compare ordinary queue
delay, worker time, receipt drainage and large-child completion in production.
Delete the policy key on adverse results and before migrating to wpc1.
Reassess on the new NFS share before enabling any limit there.
