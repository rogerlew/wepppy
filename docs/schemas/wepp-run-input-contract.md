# WEPP run input contract

## Admission before proposed input mutation (WAM-01)

Operator requested 2026-10-30; ratified in checkpoint `525e78c9f`.
Implementation and focused local conformance validated; no deployment.
Evidence: [WAM-01 validation](../work-packages/20261030_wepp_admission_before_mutation/artifacts/validation.md).

Execution submissions through `run-wepp`, `run-wepp-watershed`,
`prep-wepp-watershed`, `run-wepp-npprep`, and `run-wepp-watershed-no-prep`
MUST establish WEPP admission before applying proposed input changes. Hold the
existing run lifecycle and WEPP submission leases continuously across deferred
reconciliation, active-work admission, payload application, completion timestamp
reset, replacement receipt/hint publication, and enqueue. Preserve renewal,
ownership checkpoints and ownership-safe release. Never hold these leases across
model execution. A separate precheck followed by release and later mutation is
insufficient.

Busy-lease, active-root/descendant, and ambiguous-association rejection MUST NOT
apply proposed inputs, clear completion timestamps, replace active-job receipts
or hints, or enqueue replacement work. Reconciliation may update safely associated
prior orchestration state under the existing
[RQ response contract](rq-response-contract.md#error-responses); rejection does
not imply byte-identical Redis state. An active descendant remains a conflict
after its dispatcher finishes. Missing/terminal legacy hints remain retryable.

The shared preparation handler's batch membership (`run_group == "batch"`) and
base detection (case-insensitive, trimmed final `;;` runid component or config
of `_base`) retain synchronous configuration-only saves and their existing
message, without an execution active-job gate or enqueue. This exception does
not broaden bootstrap no-prep eligibility or add a configuration-only mode there.
No-prep submissions still use checked-out prepared files without regeneration;
the ordering rule also protects their proposed controller metadata changes.

Preserve auth, prerequisites, capability validation, payload semantics, sparse
fields, false/zero values, errors and successful job identity. Admission conflicts
may precede payload validation when both apply; admitted payload validation retains
its existing error contract. Webhook replay returns its existing identity without
reapplying inputs or duplicating enqueue. New webhook submissions follow this
admission rule; callback reservation/recovery metadata remains governed by the
[webhook contract](rq-webhook-contract.md#admission-and-recovery-matrix).

This rule governs rejection before payload application. It adds no cross-controller
transaction or rollback guarantee for payload, lease, storage or enqueue failure
after admission/application begins. Preserve existing explicit failure and cleanup
contracts. It does not freeze inputs against unrelated editing endpoints or
nonparticipating writers.

Rationale: workers reload saved controller state during preparation, so a rejected
submission must not publish parameters that admitted work can consume. Extending
the existing critical section closes this ordering gap without new infrastructure,
immutable snapshots or changes to valid configuration-only saves.

Evidence must include real NoDb persistence/reload, actual lease contention and
controlled competing submissions, and parsed prepared input under `wepp/runs/`
after accepting A and rejecting changed B. Retain existing visible controller,
intermediate, prepared-input, log and output paths and normal browse/download and
archive/restore behavior. No new artifact format, hidden path or exclusion is
introduced. Full model execution is unnecessary when exact prepared-input
readback establishes this boundary; it cannot support claims about scientific
outputs or repaired production runs.

For users and API operators: an active-work or busy-admission 409 leaves the
submitted changes unapplied. Wait for active work to finish (or use the existing
authorized cancellation workflow), then resubmit the intended values. Batch/base
configuration-only saves keep the existing input-update message. A webhook retry
with the same key replays its receipt; use the callback contract's instructions
for uncertain publication rather than assuming a 5xx means no work was accepted.

For maintainers: keep payload error translation at the application boundary and
apply payloads only after reconciliation and active-work admission within the same
lease. Keep a checkpoint after application before clearing timestamps or replacing
receipts. Preserve bootstrap's 400 payload-validation mapping versus the shared
handler's capability-authority 409. Test active descendants and lease contention
using changed values and real persisted-state readback, not source-order checks.

MRS-01 proposed checkpoint (implementation pending): [request validation](request-payload-contract.md)
rejects malformed transport and invalid supplied scalar flags/numbers before
proposed input application. This includes `delete_after_interchange` as a scalar
flag (null/blank retain no override). Preserve the admission leases and domain-error
precedence above, six routine checkbox no-override sentinels, batch/base saves,
callback replay and checked-out no-prep files. The `kslast` contract below remains
unchanged. This adds validation before writes, not rollback of later failures.
## Executable selection (CBEXEC-01)

[WEPP executable selection](wepp-executable-selection-contract.md) governs
current installed-release choices for Config Builder reruns. New selections
must satisfy paired sidecar capabilities; stored creation-time binary lists
do not block newer releases. Omission preserves the current choice. Validation
precedes mutation/enqueue, and saved selection survives normal NoDb reload.
No automatic rerun, executable-default change or project-config migration.
Implementation conformance is pending.

## kslast omission

Accepted and Forest conformance validated 2026-09-19; production rollout is
separate. This bounded contract
covers the shared WEPP parser used by JSON/form run submissions and direct
`Wepp.parse_inputs` callers. Other fields retain their current contracts.

An absent `kslast` key must preserve the saved conductivity override, including
zero, None, or a legacy absent attribute (whose property reads None). Omission
must not synthesize a new value. Explicit null, empty string, or existing
case-insensitive none-prefixed strings clear the override. Existing numeric
conversion and list/tuple/set first-nonempty selection remain unchanged;
explicit empty collections retain their clearing behavior. Other unrecognized
values retain the existing parser behavior, not a new validation policy.

Rationale: partial API submissions must not silently change an unrelated soil
parameter. Clients clearing this parameter must submit it explicitly. Initial
saturation, compiler selection, pass families, units and defaults are unchanged.
The existing NoDb lock/persistence and rq-response contracts still apply.

Evidence must exercise the real parser through its locked facade, reload durable
state and read prepared soil files. Retained artifacts use existing `wepp.nodb`,
`soils/hill_*.mofe.sol`, `wepp/runs/p*.sol`, logs and output paths, normal project
browse/download and canonical archive/restore. Failure is not completion; no
new status mechanism or error translation is introduced.

## Single User-Defined Builder exception (2026-09-25)

SUDI-01, [Single User-Defined inputs](single-user-defined-inputs-contract.md), defines the bounded creation-time exception to ordinary
Builder Disturbed support and adds independent mode5 landuse/soil uploads.
Checked projects exclude Disturbed/SBS and their dependent features across UI,
activation and direct execution, and disable buffer geometry and management
overrides. Unchecked/legacy behavior remains unchanged. The checkbox does not
select an input mode. Preserve the option through capability refresh and preserve
accepted sources across rebuilds/mode switches. Compatible cover/soil modifiers
retain their existing precedence on generated copies; all non-buffer OFEs receive
the selected single source on a mode5 build. Subsequent explicit class edits
and global mappings retain existing modification contracts and may replace
assignments; rebuilding mode5 restores uniform source assignments. These edits
do not initialize Disturbed or apply its lookup transforms. Existing authorization, response, persistence and
controller invariants remain in force. This explicit exception governs where
earlier unconditional Disturbed statements conflict; no other defaults change.
Implementation conformance is pending the SUDI-01 checkpoint and validation.

## Continuous watershed runtime budget (WRT-01)

Operator approved 2026-09-28. Continuous watershed child
jobs use `3600 * max(12, ceil(years * hillslopes / 72000))` seconds: equivalently
0.05 seconds per hillslope-year, rounded up to whole hours with a 12-hour floor.
Preserve a larger explicitly supplied pipeline timeout rather than reduce it.
This is an execution allowance, not a scientific parameter or runtime guarantee.
The empirical rationale is in [the wepp1 assessment](../investigations/20260928_wepp1_watershed_timeout_scaling/assessment.md).

Apply identically to full, full no-preparation, watershed-only, and watershed-only
no-preparation pipelines. For preparation paths use positive integral
`climate.input_years` and `wepp.watershed_instance.sub_n`. For no-preparation
paths, the owned continuous `wepp/runs/pw0.run` is authoritative: use its
hillslope-count record and final simulation-years record, without rewriting it
or requiring current saved settings to match. Both legacy master-pass prompt
and modern omitted-prompt layouts are supported. Read at most 1 MiB. Missing,
malformed, nonpositive or nonintegral workload inputs fail explicitly before
enqueueing any children; never silently substitute a default workload. Existing
valid integer-string year representations are accepted.

Single-storm modes (including batch) retain their existing timeout and do not
require continuous workload fields. Hillslope-only/preparation-only pipelines
do not read unused watershed-budget inputs. Other stage timeouts and dependency
edges remain unchanged. Compute and validate the budget before the first enqueue
in each applicable pipeline to avoid partial graphs on workload errors.

Store additive child job metadata under `watershed_timeout`: policy `WRT-01`,
`years`, `hillslopes`, `seconds_per_hillslope_year` (0.05), `timeout_seconds`,
`workload_source` (`controllers` or `prepared_run_file`) and selected `wepp_bin`.
Preserve fork-failure lineage and other existing metadata. No NoDb schema changes.
Absent optional fork metadata is normal. No new UI fields or caller-supplied
timeout overrides are introduced. This finite calculated budget has no new
arbitrary cap; it must fit the positive platform/RQ alarm range (2^31-1 seconds).
Reject an out-of-range computed/supplied budget explicitly, never silently clamp.

Existing RQ errors, auth, locks, output and completion semantics stay unchanged.
Failed jobs keep their previously stored timeout; only new submissions receive
the policy. Deployment, retrying production jobs and subprocess cleanup changes
are outside WRT-01. Validate actual serialized RQ job timeout/metadata and the
unchanged dependency tree on a disposable development run, including no-prep
source immutability.

### Omni leaf application (WRT-02)

Operator approved 2026-10-06. In the existing RQ job-pool concurrency path, new
`run_omni_scenario_rq` and `run_omni_contrast_rq` leaf jobs use the unchanged
WRT-01 options computed from the base project's normal Climate and Wepp
controllers. Compute the options once after determining that at least one leaf
of that type is required and before enqueueing the first such leaf. Apply the
same options to every affected leaf in that coordinator invocation.

Compute and validate before allocating an affected child id, writing affected
child metadata to the parent job, saving that metadata, opening the RQ Redis
connection or enqueueing an affected leaf. For contrast work this must also
precede hillslope rerun. Existing NoDb freshness and stale-run cleanup used to
determine the required contrast ids may occur first; workload failure must not
leave a new executable artifact or partial RQ graph.

Empty, absent and fully skipped scenario/contrast sets do not read unused
workload. Invalid required continuous workload fails before any affected leaf is
enqueued. Single-storm leaves retain the existing fixed base timeout and no
`watershed_timeout` metadata. Scenario and contrast coordinator jobs, summary
compilers, finalizers and all other jobs retain their current allowances.

WRT-02 changes no coefficient, floor, rounding, metadata field, alarm range,
queue, dependency, retry, cleanup, authorization, lock, model input, output or
completion behavior. Existing queued, failed and completed jobs remain
unchanged. Applying WRT-01 to a whole Omni leaf is a finite execution allowance,
not a guarantee that scenario preparation and hillslope overhead will fit; any
future coefficient or overhead amendment requires separate retained evidence and
approval. Implementation conformance was locally validated in
`adff42d6d9e38f561d41cc681e89f3386ef888c0`; deployment and production retry
remain separate operator actions.

WRT-02 adds no fan-out or concurrency cap: existing authorized scenario and
contrast selection, tracked-job conflicts, contrast batching and dependency
serialization remain the aggregate resource controls. Validate actual
serialized jobs and their `job_info` tree in a disposable real Redis queue, then
remove and verify removal of every validation job and queue.

## Soil anisotropy (SA-01)

[Soil anisotropy advanced options](soil-anisotropy-contract.md) defines optional
upper/lower overrides, omission/clearing, MOFE/hourly eligibility, finite bounds
and prepared-artifact requirements. Validate submitted overrides before other
parser mutations. No other input default, routine toggle, authorization or
persistence behavior changes. Implementation conformance pending its checkpoint.
