# Batch partial-success tracker

Updated: 2026-11-16. Server/client implementation and local validation complete.

## Progress

- [x] Inventory both workflows and consumers; retain reviewed contract decisions.
- [x] Operator approval and checkpoint `390108471`; climate addendum `0aec93f1c`.
- [x] Shared attempt publication, additive polling, failure settlement and bounded Omni recovery.
- [x] Companion client polling/resume and manifest-selected metrics/geometry.
- [x] Local real Redis/RQ timeout, actual finalizer, HTTP/download, cancellation and archive/restore tests.
- [x] Final focused regression receipts, independent review artifacts and implementation commits.
- [x] Full suite stopped at operator request: 766 passed / 32 skipped before interruption.

## Decisions and handoff

The operator approved implementation and commits. The original incident ID is
immaterial because stream-order reduction was revised to avoid its timeout;
incident identification, recovery and requeue are excluded. Preserve general
partial-success behavior and its real-timeout regression.

Normative behavior is in `docs/schemas/batch-outcome-contract.md`; cancellation,
cohort and artifact rationale is in its “Cohort, attempt and settlement” and
“Artifact layout, validation and downloads” sections. The migration guide gives
the client decision sequence and server-first rollout guidance.

Independent correctness, security and QA reviews found and closed receipt,
disclosure, graph-membership and cancellation races. Review/validation receipts
are retained under `artifacts/`. Server and external client commits are separate.
Unrelated working-tree changes are preserved.

## Validation scope and release gate

Local validation exercises real Redis jobs and timeouts, filesystem publication,
actual Culvert finalizer, signed-JWT downloads and denied foreign access, archive
restore, and external GeoPandas/Parquet readers. Synthetic scientific files are
used; feature grants, cancellation identity and some NoDb/archive adapters have
fixture boundaries. This proves local implementation behavior, not rebuilt model
science or deployed Celery/production identity and mount parity. Validate that
existing user workflow under production-equivalent conditions before rollout.
No deployment, model parameter change, production resource mutation or incident
repair is claimed. The original incident ID is not a release prerequisite.

## Commits

Server `f13e4ce6f`; external client `c56fa19a7`. Contract ancestors are listed above.
Final receipts: [validation](artifacts/20261116_validation.md),
[reviews](artifacts/20261116_implementation_reviews.md), and
[artifact readback](artifacts/20261116_artifact_readback.json).

Pushed: server implementation/closeout to `origin/master`; client `189af34e1` to
`origin/Production` after integrating upstream polling/auth changes. The original
client checkout remains unchanged. See the validation artifact push-integration
section for focused test results and commit mapping.
