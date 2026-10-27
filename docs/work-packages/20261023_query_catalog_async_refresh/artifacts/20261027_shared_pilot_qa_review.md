# Shared-batch pilot secondary QA review

Reviewer: `pilot_qa`, October 27, 2026. Reviewed after the independent
[correctness](20261027_shared_pilot_correctness_review.md) and
[security](20261027_shared_pilot_security_review.md) execution reviews.
Scope: retained evidence quality, claim traceability and documentation consistency.
No production action or runtime code change was performed by this reviewer.

## Verdict

**PASS for the completed bounded execution and its documentation.** No blocking
quality finding. The package, tracker, active ExecPlan, project board, canonical
contracts and operator notes distinguish completed deployment/pilot work from
the remaining general-enablement hold. Historical source-only preparation and
active-job holds are identified as superseded by the authorized full deployment.

The [acceptance report](20261027_shared_pilot_acceptance.md) links the
[sanitized summary](20261027_shared_pilot/summary.json) and
[deployed preflight](20261027_shared_pilot/deployed_preflight.json).
Private scope/job identifiers and evidence-directory locators are not needed in
the public claim chain and are not reproduced here.

## Independent evidence checks

- Recomputed all 14 published private-evidence digests; every retained file
  matches. Recomputed all six deployed source-file hashes against the checkout;
  both hosts also have equal configuration and native-library fingerprints.
- Reconciled final job and binding records: one inventory plus 16 refresh jobs,
  all finished, seven distinct executing workers, zero outstanding/uncertain
  work and no recorded failures. Final admission is paused for
  `acceptance_readback_complete`.
- Compared registration, pause and final manifest/deadline records: they are
  identical. The paused result has zero outstanding work; resume did not reset
  authority or cumulative budgets.
- Checked both eight-scope readbacks and all 48 source-versus-copy row-count
  comparisons. Both record unchanged source and excluded sentinel. These checks
  complement the correctness/security review of raw publication verification
  before consumer calls; queue status alone does not support acceptance.
- Recomputed the enqueue/end timeline peak of seven and the separate sampled
  peak of four across 12 observations. Recomputed the 90.32-second observation
  gap and completion 1,605.36 seconds before the original admission deadline.
  Neither a sampled peak nor the intentional drained gap is presented as
  uninterrupted observation.
- Matched the cleanup summary to its retained readback: nine old fixture paths
  absent, 711 scientific-source hashes and eight catalog hashes reported
  verified, no observer lease/outstanding work, eight compatible unsuspended
  consumers and general async disabled. This reviewer checked retained evidence;
  the post-retirement filesystem/hash scan was performed by the operator.

## Residual debt and follow-up boundaries

- **Raw metadata retention:** original status/incarnation bytes were replaced
  during canonical retirement before a separate snapshot. Exact original-status
  replay is unavailable; manifest, controller readbacks, catalog/source hashes
  and receipt history retain the accepted evidence chain. The limitation is
  explicit in acceptance, tracker and ExecPlan. The durable
  [retirement procedure](../../../dev-notes/query-catalog-refresh-operations.md#completed-pilot-and-owned-fixture-retirement)
  now requires snapshotting those metadata bytes before invalidation. Do not
  reconstruct missing bytes or describe this execution as complete raw-state
  retention.
- **REV-01:** the unchanged controller can return `safely_stopped` before readback
  after the admission deadline, even when admitted work has drained. This fails
  safe and was not exercised. Retain the correctness finding at
  `tools/query_catalog_pilot.py:491`; a future bounded conformance repair should
  verify post-deadline readback without admitting work or resetting budgets.
- **Capacity:** one ordinary job was already running; its historical 8.013 ms
  wait does not measure arrival latency under pilot contention. No new ordinary
  arrivals were observed. Whole-fleet cycle progress, oldest-pending age and
  ordinary-arrival delay remain separate acceptance gates. General enablement
  remains disabled and is not authorized by this pilot PASS.

No new abstraction, dependency or runtime test surface was introduced by this
closure. Repeating prior code suites would not repair the missing historical
metadata or expand the pilot's capacity evidence. Documentation lint and direct
evidence checks are the appropriate validation for this change.

Validation: `wctl doc-lint --path docs/work-packages/20261023_query_catalog_async_refresh`
passed all 63 Markdown files with zero errors or warnings. The `uk2us` preview
for this review produced no changes.
