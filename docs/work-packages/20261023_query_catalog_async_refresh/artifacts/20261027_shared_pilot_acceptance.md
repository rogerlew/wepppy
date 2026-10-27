# Production shared-batch pilot acceptance

Date: 2026-10-27. **Bounded pilot PASS; general fleet enablement HOLD.**
The user resumed pending work after the full canonical deployment of `0da9c9071`
to wepp1–3. This supersedes the earlier active-job deployment hold and optional
source-only backport preparation. No further runtime source or configuration
changes were required for this pilot.

## Evidence and execution

[Deployed preflight](20261027_shared_pilot/deployed_preflight.json) records matching
application and native hashes on wepp1/wepp2, UID1002/GID130, disabled general
mode and eight genuine compatible, unsuspended batch consumers. No worker
registration was fabricated. [Sanitized summary](20261027_shared_pilot/summary.json)
retains aggregate outcomes and hashes of private evidence. Exact job IDs, owned
scope locators, ordinary-job identifiers and raw observations remain in private
operator storage on wepp1, with a private local review copy. Public traceability
uses the sanitized summary and evidence-file hashes, not private locators.

The unchanged installed `tools/query_catalog_pilot.py` ran `prepare`, `register`,
`run`, `pause` and explicit `resume` inside wepp1's existing batch container.
Eight exclusively owned scopes plus an excluded sentinel each received the
retained 79-Parquet, 73,328,103-byte scientific fixture. No user project changed.

- One inventory job and 16 refresh jobs finished, exactly two refresh jobs per
  approved scope. Seven actual workers on both production batch containers
  executed the jobs (11 and six jobs respectively).
- Both artifact waves passed: source hashes, schemas, catalog identity/digest,
  exact path containment, 48 DuckDB/query-engine checks and eight explicit
  receipt acknowledgments. Raw artifact checks preceded consumers; consumers
  did not repair catalogs. The source and excluded sentinel stayed unchanged
  throughout acceptance.
- The reconstructed enqueue-to-terminal timeline peaked at seven outstanding
  jobs, matching the admission cap. Ten-second observations sampled a maximum
  of four. All counters remained within the original 25-refresh/two-inventory
  budgets; final outstanding, uncertain and failed counts were zero.
- The inventory finished before the explicit pause. The controller exited
  `safely_stopped` with one inventory, zero refresh jobs and no outstanding work.
  An early resume was rejected by the existing observer lease. After confirmed
  expiry, explicit resume preserved the manifest, generation, deadline and
  counters. The retained 90.32-second observation gap was paused and drained;
  no admitted execution spanned it. This is not uninterrupted observation.
- One ordinary batch job was already running before registration; its earlier
  enqueue wait was 8.013 ms. No new ordinary arrivals or waiting backlog were observed
  during the pilot. These observations prove coexistence, not new-arrival delay
  under contention or whole-fleet throughput.
- The resumed controller completed both waves in 76.23 seconds and stopped
  admissions with `acceptance_readback_complete`, well before its original
  30-minute admission deadline. Public job trees omitted private paths,
  results, actor details and tracebacks.

## Cleanup and evidence limits

After successful acceptance, exact marker, scope/incarnation and inode checks
were repeated inside each canonical lifecycle guard. Only the nine owned scratch
scopes were invalidated and atomically moved on the same filesystem to private
`retained-fixtures` storage outside managed roots. All nine old paths are absent;
711 retained Parquet hashes and eight final catalog hashes still match. External
coordination lock files, receipt histories, Redis ledger, budgets and private
evidence remain intact. The controller lease expired; no pilot work remains.
All eight batch consumers remain compatible and ordinary dequeue is unsuspended.

Canonical lifecycle retirement replaced the original refresh `status.json` and
incarnation files. Their original status bytes were not separately snapshotted.
The controller verified publication status and acknowledgments before retirement;
retained readbacks, immutable manifest, receipt histories and unchanged catalog
bytes preserve that acceptance chain, but an independent byte-for-byte replay of
the original status JSON is no longer possible. Future retirement must snapshot
those metadata files before invalidation. Do not reconstruct missing evidence.

Independent [correctness](20261027_shared_pilot_correctness_review.md) and
[security](20261027_shared_pilot_security_review.md) reviews pass. Secondary
[QA](20261027_shared_pilot_qa_review.md) records the final documentation review.
The low-priority controller deadline limitation identified by correctness review
was not exercised: an expired, drained controller stops before automatic
readback. Such a result must remain incomplete unless separately verified; it
must never be relabeled successful from queue state alone.

## Remaining boundary

The authorized implementation, deployment and bounded pilot execution are
complete. General async is still disabled and explicit production roots remain
unset. Whole-fleet capacity is not established by eight small owned scopes:
complete-cycle/oldest-pending-age and ordinary-arrival delay acceptance across
the configured fleet remain separate enablement gates. The canonical pilot
contract expressly excludes general enablement even after success. No further
component-only scans or repeated equivalent pilots are needed to close this
bounded execution; a broader rollout needs its own bounded acceptance scope.
