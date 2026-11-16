# Batch result outcomes

Status: BATCH-OUTCOME-01 approved by the operator on 2026-11-16; implementation pending.
This specializes [RQ polling](rq-response-contract.md) for ordinary batch and
culvert root jobs. It does not change generic RQ status, webhook settlement,
scientific execution, retry selection, cancellation, or access policy.

## Public polling schema

Enrolled root responses from jobinfo (including batch jobinfo) and jobstatus
include the same `batch` object. Legacy jobs and unrelated/child jobs omit it.
Restricted catalog projections never gain this field. Only server-registered
`run_batch_rq`, `run_culvert_batch_rq`, and explicit
`run_culvert_batch_finalize_rq` roots can enroll; arbitrary metadata
cannot enroll another function or supply paths or download URLs.

| Key | Type and meaning |
| --- | --- |
| `schema_version` | Integer, exactly 1 |
| `attempt_id` | String, original root RQ job ID |
| `state` | `running`, `finalizing`, `completed`, or `failed` |
| `outcome` | Null until terminal; then `success`, `partial_success`, or `failed` |
| `total` | Nonnegative integer, frozen selected logical-run cohort size |
| `succeeded` | Nonnegative integer, validated usable selected runs |
| `failed` | Nonnegative integer, failed or unusable selected runs |
| `skipped` | Nonnegative integer, selected runs with an explicit domain skip |
| `results_available` | Boolean; true only after validated artifact publication |
| `download_url` | Null or same-origin, credential-free download path |
| `reason` | Null or one of the codes below |

Before settlement counts are zero; `total` is the frozen cohort size. Before
cohort selection finishes, total is zero and state is running. At terminal
settlement succeeded + failed + skipped equals total. Successful publication
with at least one usable run yields completed/success if failed is zero, or
completed/partial_success otherwise. Domain skips do not make partial success.
Zero usable runs yield completed/failed, availability false, null URL and reason
`no_usable_results`. A finalizer or dispatch failure yields failed/failed,
availability false, null URL and reason `finalization_failed` or
`dispatch_failed`. Explicit root/tree cancellation yields failed/failed with
`canceled`; it must never publish a success. Missing required RQ identity before
settlement yields failed/failed with `execution_record_missing` once its absence
is proven (a Redis outage is an endpoint error, not missing execution).
Unsettled cohort members on infrastructure failure count as failed; domain skip
counts require affirmative evidence. Reason is null for other cases. No exception
text, filesystem paths, per-run IDs, credentials or arbitrary metadata enter
this bounded object. Existing sanitized leaf exception responses remain intact.

Clients prefer a present version-1 batch state over aggregate status for result
readiness: running/finalizing continues polling even if status is failed;
completed plus results_available permits download; terminal without availability
is a visible no-results failure. Unknown versions are unsupported, never success.
Absent batch retains the client's explicit legacy aggregate-status behavior.
HTTP/auth errors retain the canonical RQ error envelope and current access rules.

## Cohort, attempt and settlement

Ordinary batch freezes exactly the selected retry/full-rerun leaves, not every
existing directory. Already-complete leaves omitted by existing retry selection
are outside the cohort, not counted as failed or skipped. Empty selection settles
with no usable results; it does not remove historical project outputs. Culvert
freezes the accepted logical runs, including explicit validation failures and
no-outlet skips. Stray directories never enlarge either cohort.

Dispatch persists enrollment and cohort before releasing scientific work. Each
member records its exact current-attempt leaf job IDs; existing ordinary batch
hillslope/watershed handoffs and linked Omni dependencies remain authoritative.
Finalization waits for every relevant job, including dynamically linked Omni
work, to terminate and must not settle while linkage is pending. Existing
failure-tolerant dependency helpers are reused. Ordinary Omni compile/finalizer
jobs blocked behind a failed required scenario must be reconciled by a bounded
extension of the existing deferred-workflow helpers: they are terminally canceled as blocked,
never released to consume missing scientific outputs. The batch finalizer's
terminal dependency then settles; the selected parent run is failed. This
bounded queue change must retain job/dependency evidence and preserve all
unaffected scientific success-only edges. Prove it with a real failed Omni
scenario and a successful sibling, not only a mocked terminal Omni job.
The existing `WepppyRqWorker.handle_job_failure` observes exhausted failures
and invokes this reconciler after RQ records failure; automatic retry remains
untouched. Enrolled-root polling invokes the same reconciler as a recovery
trigger for missed worker notification/abandoned jobs. This is the only
additional polling queue-mutation exception. Under the resource lease, validate
the entire affected graph against the enrolled root/attempt/selected leaf and
exact server-recorded Omni membership before any cancellation. Cancel only
strictly blocked deferred Omni scenario/compile/finalizer descendants; preserve
running/queued independent work and the ordinary batch finalizer itself. Recheck
all RQ states atomically at mutation, detach canceled dependencies through the
existing RQ mechanisms, and explicitly release the failure-tolerant batch
finalizer only when all dependencies are terminal and links are complete.
Foreign membership or changed state produces no partial mutation. Do not call
`reconcile_deferred_workflow` with a broad association: it traverses dependents
and would cancel the batch finalizer too. This requires a bounded helper change,
not a claim that existing reconciliation already provides selective settlement. A caught application failure and
an uncaught/timeout/abandoned RQ failure both classify the affected logical run
as failed once retries are exhausted; automatic queued/scheduled/eligible
retries remain unsettled and cannot trigger durable failure publication. A worker killed before metadata publication cannot inherit old success.
A terminal failed/stopped/canceled required job overrides a success marker.

Only a correctly associated current finalizer may publish a terminal artifact.
Its root, workflow, resource and cohort must agree with persisted enrollment.
Use existing submission/resource locking to fence replacement attempts and
publication. Old finalizers cannot replace the current attempt pointer. A normal
retry is a new root ID; requeued finalizers of the same attempt are idempotent
and may not replace a committed terminal result with different bytes. A committed
failed attempt requires a new submission to produce a different result.

Explicit culvert finalize creates a new publication attempt identified by its
own RQ job ID, freezes the registered cohort and each latest per-run execution
receipt, and validates those source executions. It may include unchanged valid
runs from the original dispatch plus successfully retried runs. A standalone
single-run retry remains a leaf operation without `batch`; it invalidates the
current pointer before run replacement but preserves immutable old ZIPs. The
next explicit finalize supplies the new batch outcome. Retry/finalize admission
and publication share the existing resource lease and active-job checks; no
leaf may mutate packaged sources while publication is in progress. Refinalizing
legacy runs without sufficient execution identity cannot certify version-1
readiness; the legacy diagnostic finalizer remains usable and reports that
missing evidence explicitly. No reconstruction from directory names is allowed.

Poll reads reconcile dispatch/finalizer failure from the verified RQ identities
when no terminal publication exists, so process death does not leave endless
running. Terminal observation is persisted under the same resource lock with
an identity recheck. This is an explicit narrow exception to observational GET
semantics: polling may persist verified terminal failure for an enrolled
current attempt and perform only the verified blocked-Omni transition above. Lock acquisition is nonblocking; contention or persistence
failure returns canonical HTTP 503 with code `batch_reconciliation_unavailable`,
never an invented durable success/failure receipt. No scientific state is written.
Normal project inspection shows the last persisted state and source job IDs;
unreconciled running/finalizing records are labeled last-observed, not live truth.
Opening the normal project status surface must use the same reconciliation path.
Polling never creates success or constructs scientific
artifacts. Root/finalizer and all required leaf/Omni execution identity records use
non-expiring retention until explicit project cleanup; a fast successful leaf
must remain provable after a sibling exceeds its 12-hour timeout; no new scheduler or queue is introduced.

## Artifact layout, validation and downloads

Use visible `batch_results/<attempt_id>/` under the existing batch root for
`summary.json`, `runs.json`, and `results.zip`, with a root-level
`batch_results/current.json` attempt pointer. These are ordinary project records
in browser and archive/restore. Working and failed publication records stay in
the same visible attempt directory. This follows the existing ordinary batch
`batch_handoff/` convention. Existing run directories, input records, failed
work products and logs remain in place. The historical culvert
`weppcloud_run_skeletons.zip` remains a diagnostic/legacy artifact and is never
used to prove version-1 readiness.

Both workflows publish an attempt-specific ZIP using the existing authorized
file download route: `/weppcloud/batch/{name}/download/batch_results/{attempt}/results.zip`
or `/weppcloud/culverts/{uuid}/download/batch_results/{attempt}/results.zip`.
Identifiers are validated and URL path components encoded; path lookup never
uses a client-supplied absolute path, serialized `wd`, or metadata URL. No new
endpoint, download credential, capability, or access-policy exception is added.
Existing feature projections must filter batch metadata before disclosure.

The ZIP contains `runs.json` and `runs/<id>/...` for validated successful cohort
members only. `runs.json` has `schema_version: 1`, `attempt_id`, `workflow`
(`batch` or `culvert`), and `runs`, an array of objects with `run_id` (string),
`status` (`success`, `failed`, `skipped`), and `reason` (null or a bounded code:
`execution_failed`, `outputs_invalid`, `no_outlet`, `no_result_outputs`, `not_executed`). Failed and
skipped members appear in this manifest, never as scientific result directories.
Manifest run IDs must be unique safe single path components. Counts and ZIP
membership must match this manifest exactly. Existing detailed diagnostics stay
accessible through the ordinary project and job inspection surfaces.

A success marker alone is insufficient. Culvert success requires current-attempt
successful leaf execution, parseable `wepp/output/interchange/loss_pw0.out.parquet`
with the consumer's `value` column and required metric rows 0 through 10, plus
parseable GeoJSON FeatureCollections in `dem/wbt/subcatchments.WGS.geojson` and
`dem/wbt/channels.WGS.geojson` (the client uses subcatchments for hillslopes too). Validate
features and their identities against the selected run; never synthesize zero
metrics for failed/missing outputs. Ordinary batch success requires current
completion under its enabled directives and parsed outputs: enabled watershed
execution requires watershed loss interchange; enabled hillslope execution
requires `H.loss.parquet` for continuous climate and `H.pass.parquet` for
supported single-storm climate (the producer intentionally omits storm loss
interchange). Read the leaf climate mode; do not infer it from missing files.
Zero-row optional/event tables and empty optional geometries remain valid when
structurally parseable; required consumer metrics/subcatchments retain their
semantic validation. Optional absent modules remain absent, not errors.
Prep-only/no-model selected members are skipped with reason
`no_result_outputs` (scientific results were not requested); an all-skipped
selection produces no usable result ZIP and uses batch reason
`no_usable_results`; their ordinary RQ completion and prepared project files
remain unchanged. Linked Omni failure makes its selected parent run failed.
Missing/corrupt required outputs classify only that member as outputs_invalid.

The new ZIP includes only the manifest, scientific interchange files under
`wepp/output/interchange/`, and consumer geometry under `dem/wbt/` (GeoJSON only).
The derivative ZIP is a baseline WEPP result bundle. WATAR and Omni outputs
retain their existing project download surfaces and are not copied into this
bundle; their execution still participates in ordinary leaf completion. A
WATAR-only retry can include its unchanged baseline WEPP outputs after parsing
them, but cannot claim those baseline outputs were recomputed by the retry. Do not include logs, NoDb
files, input credentials or recorder files in the derivative ZIP. These remain
available through their existing project access policy.
The exact file extension allowlist is `.parquet` under the interchange subtree
and `.geojson` under the WBT subtree, plus the generated `runs.json`. Apply
existing browse raw and resolved path checks, secret, Root-only and recorder
exclusions to every member and resolved symlink target, not only to the ZIP
filename; inspect and parse every delivered Parquet/GeoJSON file. Reject escaping paths and
symlink targets rather than copying foreign data. A valid in-root file symlink
may be materialized; directory symlinks are not traversed. Do not weaken existing
download containment or authentication to expose these records.

Write to visible temporary files in the attempt directory, close and read back
the ZIP (CRC, manifest, semantic outputs and membership), then atomically rename
it. Publish summary last by atomic replacement under the resource lock; Redis
may mirror this authoritative durable record but cannot advertise readiness
before it exists. A partial ZIP or failure writing a manifest/summary leaves
availability false and a visible publication failure. The two-file commit is
ordered: a ZIP without a committed summary is not ready. No fixed legacy ZIP,
mtime, NoDb flag or prior-attempt summary can imply readiness.

## Retention, restore and consumer compatibility

Retain attempt summaries/manifests/results with the existing project retention
and explicit cleanup lifecycle; no additional automatic deletion is introduced.
Redis expiry after terminal publication does not erase durable project evidence.
Expired job IDs retain existing not-found polling behavior; do not resurrect jobs
from a path search. Normal project inspection can show historical completed
results with their recorded attempt. Restore preserves artifact bytes and
historical status, but cannot enroll an RQ job or authorize a new attempt.
Reader rollback ignores additive files/fields and keeps legacy behavior; it does
not reinterpret partial results as full success.

The external Culvert client must use the manifest's success IDs for metrics,
hillslopes, channels and counts, verify attempt identity against polling, and
report omitted IDs/counts visibly. Resume probing must also recognize a running
or available partial batch even when aggregate RQ status is failed. The client resolves download paths only against its configured WEPP origin,
checks the exact batch/attempt path, and rejects cross-origin redirects before
forwarding any authentication. A returned URL is not authority to contact an
arbitrary host. Client
adoption is a separate repository delivery and end-to-end gate. Deploying only
the server does not close that gate.

## Acceptance and rationale

Keep RQ diagnostics separate from artifact usability: masking a failed child
would hide the timeout and still would not prove downloadable results. A visible
attempt-specific ZIP gives both workflows an unambiguous publication boundary
without changing existing diagnostic downloads. A selected-only cohort avoids
silently treating old runs as fresh output.

Required evidence includes both workflows' success, partial timeout, caught
failure, all failed, empty/all-skipped, dispatch/finalizer crash, failed ZIP or
summary publication, stale success marker, retry fencing, cancellation, Redis
expiry, archive/restore, valid authorization and hostile/foreign paths. Exercise
a real RQ timeout, actual HTTP download and semantic archive readback, plus the
real external client's metrics/geometry filtering. Directive cases separately
include watershed/hillslope disabled, optional modules absent, already-complete
retry, full rerun and linked Omni. Mocks alone cannot close publication,
authorization, process-boundary or artifact acceptance.

Implementation clarification (2026-11-16): climate-appropriate validation preserves
existing single-storm behavior; the initial blanket hillslope-loss predicate was
inconsistent with the owned producer. No scientific defaults or formulas change.
