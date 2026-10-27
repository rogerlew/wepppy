# Shared-batch pilot correctness and operational review

Reviewer: `pilot_review`, October 27, 2026. Scope: the existing bounded pilot
after the separately authorized full deployment of `0da9c9071`. No production
operation or runtime code edit was performed by this reviewer.

## Verdict

Preflight, bounded shared-batch execution and owned-fixture retirement **PASS**.
Independently inspected the private execution, observation, recovery, artifact
and cleanup records; no blocking correctness finding remains for this observed
pilot. One low-severity controller limitation and one evidence-retention
limitation are recorded below.
This is not whole-fleet capacity acceptance or authority for general enablement.

## Confirmed preflight

Independently checked [deployed_preflight.json](20261027_shared_pilot/deployed_preflight.json):
both hosts run as UID1002/GID130, report eight compatible unsuspended consumers,
have no queued batch jobs, and retain identical disabled catalog configuration.
All six deployed source hashes match the checkout; native hashes and selected
dependency versions match between the two hosts.

Unset `QUERY_CATALOG_ROOTS_JSON` is valid in disabled mode: the canonical default
root map still identifies the owned scratch scopes. No environment override,
spoofed capability, source overlay, service restart, or general enablement is
needed for this pilot. The earlier source-only/backport rollout evidence is
historical; today's actual deployment/source readback is the relevant baseline.

## Acceptance checks

Review the frozen eight-scope manifest and excluded sentinel; actual job lineage
and immutable cumulative budgets; complete observation stream and ordinary wait
measurements; inventory and explicit-receipt waves; raw catalog identities,
schemas, source hashes and acknowledgments before consumer queries; query
results and unchanged publication after consumers; final drain and owned-resource
disposition. A successful RQ status alone is insufficient.

The planned pause after the first inventory, drain, observer-lease expiry and
explicit resume is compatible with the fixed manifest/window/budgets. A rejected
resume while the prior observer lease is still live is expected. Preserve the
rejected attempt and pre-pause result before later invocations overwrite the
controller's `result.json` or `preflight.json`. Do not intentionally pause midway
through receipt creation: that state requires explicit partial-wave recovery.

## Observed execution

- The pause and final result preserve the original registered manifest,
  generation, deadline and budgets. The initial inventory finished, explicit
  pause drained with zero refresh admissions, a premature resume was rejected
  while the observer lease remained owned, and explicit post-expiry resume used
  the same authority. No counter/deadline reset occurred.
- All 17 admitted jobs finished: one inventory and two refreshes for each of the
  eight scopes. Seven registered workers across both production batch containers
  executed them. Final outstanding, uncertain and failure counts are zero;
  admission is paused with `acceptance_readback_complete`.
- Both readbacks contain eight catalogs with 81 entries each and 24 passing
  consumer/source count comparisons. All 79 scientific Parquet sources
  (73,328,103 bytes per fixture) retained their hashes/schemas. Eight explicit
  receipts have publication acknowledgments. Source and excluded sentinel
  remained unchanged during acceptance; consumers did not repair publication.
- Every participant observation reports eight compatible unsuspended consumers.
  Ten-second samples peak at four outstanding jobs; reconstruction from retained
  enqueue/end timestamps peaks at seven. All 17 public job trees omit private
  project paths, result payloads and exceptions.
- The 90.32-second observation gap is the deliberate paused/drained controller
  restart: the inventory was already finished and refresh admissions began only
  after resume. It is retained as a gap, not continuous observation evidence.
- The single observed ordinary batch job had already started before the pilot.
  Its recorded 8.013 ms enqueue wait predates the experiment. No new ordinary
  arrival or backlog was observed: this proves coexistence with ongoing ordinary
  work, not arrival-latency behavior under pilot contention.
- The final observation precedes the original admission deadline by roughly
  1,605 seconds. The late-readback limitation below was not exercised.

The private directory is mode `0700`; exact identifiers, fixture locators and raw
ordinary-job records are not copied into this review.

## Owned-resource disposition

The operator retired the exact nine marker-bound fixtures under their existing
lifecycle guards after checking path/scope/directory identities, terminal jobs
and paused admission. Canonical invalidation rotated each incarnation before an
atomic same-filesystem rename outside managed roots into private retention.
This prevents the sentinel's deliberate pending receipt from becoming future
ordinary maintenance work. External coordination guard inodes and Redis
accounting/evidence were preserved.

The private cleanup records and their hashes in
[summary.json](20261027_shared_pilot/summary.json) are consistent: all nine old
paths are absent, all 711 retained Parquet hashes and eight published catalog
hashes passed operator readback, outstanding work and observer leases are zero,
all eight consumers remain compatible/unsuspended, and general enablement stays
disabled. This reviewer independently checked the retained records and all 14
published private-evidence hashes; the post-retirement filesystem/hash scan was
performed by the operator.

**Evidence-retention limitation:** original refresh `status.json` bytes were not
separately snapshotted before canonical invalidation replaced them. The reviewed
controller checked publication identity, status and receipt acknowledgments
before recording artifact verification; the fixed manifest, readbacks, old/new
incarnation mapping, receipts and unchanged catalog/source bytes remain retained.
The observed bounded acceptance therefore stands, but exact replay of the
original status/acknowledgment JSON is unavailable. No reconstruction is claimed.
Future fixture retirement should snapshot those metadata bytes before
invalidation.

## Residual controller limitation

**REV-01, low; nonblocking for an observed completion inside the admission
window.** `tools/query_catalog_pilot.py:491` checks for a non-active state before
raw artifact readback. If the already-admitted second wave finishes only after
the 1,800-second admission deadline, `pilot_status` reports `expired` and the
controller returns `safely_stopped` without verifying those completed artifacts.
The canonical contract permits drain/readback after the admission deadline.

A local, read-only controller reproduction with completed-wave phases, expired
state and zero outstanding work returned `safely_stopped` with no `raw_ready` or
`verify_artifacts` call. This cannot create false success; retain an explicit
late-readback disposition or make a bounded controller conformance repair if
that case is encountered. Do not reset the pilot deadline or budgets to recover.

## Claim limits

The live pilot must retain any ordinary-job observation gaps and distinguish an
idle shared queue from measured contention. Eight owned scopes cannot establish
the fleet's 24-hour complete-cycle target. Historical full discovery, component
profiles and the scientific acceptance remain separate evidence. General async
refresh stays disabled after the bounded pilot unless a separately authorized
rollout satisfies its remaining capacity gates.
