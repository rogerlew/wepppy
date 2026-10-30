# WAM-01 consumer and state assessment

Static inspection at `29716c1bd9a24dacf1cb45e05a11b2aa44a5378e`, 2026-10-30 UTC.
Bounded search: all `apply_wepp_run_payload` and shared-handler callers, WEPP
no-prep enqueue helper, webhook wrapper, request lifecycle middleware, WEPP
reconciliation/active-tree helpers and preparation reloads. Not repository-wide
concurrent-edit coverage. Runtime regression and prepared-input evidence pending.

## Consumer matrix

All paths below are relative to the repository root.

| Consumer / dependency path | Context and evidence | Disposition |
| --- | --- | --- |
| `wepp_routes.py`: run-wepp → `_handle_run_wepp_request` → apply → lock → reconcile/ensure | Valid changed payload persists before active rejection; hillslope dispatcher reloads controllers | confirmed defect (static) |
| Same handler: run-wepp-watershed | Same ordering, watershed prerequisite retained | confirmed defect (static) |
| Same handler: prep-wepp-watershed | Same ordering, no watershed prerequisite gate | confirmed defect (static) |
| `bootstrap_routes.py`: run-wepp-npprep → apply → `_enqueue_no_prep_job` | `enforce_wepp_singleflight=True`; metadata mutates before rejection; prepared files intentionally not regenerated | confirmed defect (static) |
| Same module: run-wepp-watershed-no-prep | Same apply-before-helper ordering and single-flight gate | confirmed defect (static) |
| `_enqueue_no_prep_job`: run-swat-noprep | No call to WEPP payload application; shared helper behavior must stay unchanged | verified unaffected by this payload ordering (static); regression required if helper changes |
| Shared handler: batch and `_base` | Applies payload then returns configuration-only message; authorized save, not execution admission | verified unaffected by defect; preservation tests pending |
| `webhooks.Submission.replay` / `submission_boundary` | Replay returns before apply; new submission reserves callback then follows defective handler; finally cleans prepublication receipt | replay verified unaffected (static); new submissions confirmed defect |
| `rq_engine.__init__.run_mutation_lifecycle_middleware` | Authenticated HTTP requests hold lifecycle lease across handler; does not inspect active worker tree | verified insufficient to prevent defect; real contention coverage pending |
| `wepp_rq_stage_prep._prep_slopes_rq` / `_prep_soils_rq` | `Wepp.getInstance(wd)` / `Watershed.getInstance(wd)` reload before preparation | confirmed potential consumer path (static); changed scientific result unresolved |

## Runtime state matrix

These are states, independent of which payload fields are submitted.

| State | Required outcome / policy | Evidence still required |
| --- | --- | --- |
| Fresh never-run, absent optional job hints | Accept if ordinary prerequisites hold; no new corruption classification | Real first admission/persistence |
| Present-empty or terminal hints / completed run | Retry; reset timestamps only after admission and successful application | Reload and metadata assertions |
| Active root | Canonical 409 `conflict`, preserve proposed fields/receipts/timestamps | All five routes |
| Finished parent, active queued/started/scheduled child | Same conflict | Real associated job tree |
| Recoverable deferred prior graph | Conditional safe cancellation, then admission/apply | Existing recovery suite plus route integration |
| Deferred plus active descendant | Conflict, no proposed inputs; permitted cleanup only | Mixed tree test |
| Missing legacy hint/job | Existing retry semantics | No invented required field |
| Copied/cross-run/wrong-family/origin or ambiguous graph | Fail closed without proposed mutation | Association failure tests |
| Busy family or lifecycle lease | Canonical existing 409; no payload apply | Real Redis lock and file fence interleaving |
| Batch group or base run/config | Configuration-only save, existing message, no execution gate/enqueue | Batch plus base normalization variants |
| Working/failed/completed artifacts | Preserve visibility and prior artifacts; no false completion | Browse/archive/restore evidence for representative fixture |
| Webhook accepted duplicate | Same identity, no mutation/enqueue | Real replay/store regression |
| New webhook with active work | Conflict; callback cleanup allowed, active receipts preserved | Callback-bearing rejection |

## Payload dimension and errors

Use changed valid values across WEPP/soils/watershed, sparse omission, explicit
false/zero, legacy fields and base normalization independently of states above.
Do not claim every Cartesian combination tested. Invalid payload after admission
keeps each route's existing mapping: the shared handler uses 400 or
capability-authority 409; bootstrap no-prep maps all
`WeppRunPayloadValidationError` cases to 400. NoDb contention keeps the existing
409 input-lock message. Prerequisite rejection remains before apply (response
contract Error responses). Storage/enqueue failures are exceptional existing 5xx;
lease loss fails closed using existing ownership semantics. Missing optional
hints are normal, whereas malformed associations are expected 409 conflicts.
Webhook invalid/unsupported/idempotency/uncertainty cases retain their matrix in
`rq-webhook-contract.md`. No new public error category is proposed.

## Critical section and downstream evidence

`SubmissionLease` renews each 30 seconds to 120 seconds and checkpoints renew
ownership explicitly. Acquire lifecycle, then WEPP family, then existing payload
controller locks; preserve the payload's internal controller ordering. Move only
local validation/persistence work under the family lease. Inspect revegetation
cover-transform and SWAT parameter side paths for duration and lock inversion
before implementation; do not wrap model execution or remote computation.
Checkpoint immediately before application and after it, before timestamp/receipt
writes, while retaining existing pre-enqueue checkpoint and finally release.

Evidence chain: payload A → real durable controller → reject changed B → real
preparation → parse exact soil/slope parameter in `wepp/runs/`. Retain paths,
hashes and parsed values. Model output/report stages are outside the claim; no
full simulation is needed for prepared-input isolation. No-prep variants prove
controller rejection and byte-preservation of checked-out prepared files. Existing
normal project browser/download and archive/restore paths remain unchanged and
must retain representative inputs and failure records.

## Additional static feasibility evidence

`Revegetation.load_cover_transform` performs local feature checks, a NoDb setter
and `shutil.copyfile` from the installed cover-transform directory; no remote or
model operation. `_apply_swat_channel_params` checks Ron mods and calls the SWAT
input parser. No lifecycle reacquisition was found in these modules. Their
NoDb/parser and filesystem failure paths still require admitted-failure coverage;
this inspection is not a duration benchmark or a complete lock-order proof.
Existing real-facade fixture precedent is
`tests/nodb/test_wepp_input_parser.py::test_kslast_omission_survives_real_facade_persistence`.
Real coordination/recovery suites include `tests/rq/test_submission_recovery.py`
and `tests/rq/test_wepp_singleflight_tracking.py`.
