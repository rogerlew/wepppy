# WEPPcloud Project Forking Details

> **See also:** [AGENTS.md](../../AGENTS.md) for RQ Background Tasks and Adding an RQ Background Task sections.  
> **Related:** [weppcloud-project-archiving.md](weppcloud-project-archiving.md), [controller-contract.md](controller-contract.md), [trigger-refactor.md](../mini-work-packages/completed/trigger-refactor.md)

## Introduction
The forking system clones an existing WEPPcloud run into a new run directory. The fork console lets users submit a fork job, monitor live status output, and open the new run when the job completes. Forking can optionally "undisturbify" the run by clearing disturbance artifacts, rebuilding landuse/soils, and rerunning WEPP.

## Fork Console UI
Template: `wepppy/weppcloud/routes/fork_console/templates/rq-fork-console.htm`  
Control: `wepppy/weppcloud/templates/controls/fork_console_control.htm`

- Uses `control_shell` with a console-style status panel and stacktrace panel.
- Shows source run ID (read-only), an undisturbify checkbox, a `Skip wepp/runs and wepp/output` checkbox, and submit/cancel controls.
- Emits bounded stage and heartbeat updates via the `<runid>:fork` StatusStream channel only while a job is tracked.
- Renders authoritative job status plus start/end timestamps in the status panel (`#rq_job`) via polling.
- Replaces copy-heartbeat text in a live status region instead of appending it to the console log.

## Front-End Orchestration
Script: `wepppy/weppcloud/static/js/fork_console.js`

- Reads run context from `data-fork-console-config` and the form.
- Submits the fork request with `fetch` to `/rq-engine/api/runs/<runid>/<config>/fork` (form-encoded `undisturbify` + `skip_wepp_runs_output`).
- Starts StatusStream on channel `fork` only after submission or session restoration and uses `controlBase` polling to keep job status authoritative:
  - `set_rq_job_id(...)` polls `/rq-engine/api/jobstatus/<job_id>` for status/started/ended timestamps.
  - Polling failures fetch `/rq-engine/api/jobinfo/<job_id>` to populate stacktraces.
  - WebSocket `FORK_COMPLETE`/`FORK_FAILED` triggers request immediate job-status reconciliation but do not terminate the UI by themselves.
  - Poll-origin `job:completed`/`job:error` handlers perform the idempotent terminal UI transition.
- Stores source/config/job/destination identifiers (never tokens) in `sessionStorage` so same-tab reload restores polling.
- Reconciles status immediately on `visibilitychange`, `focus`, and `pageshow` after browser throttling or suspension.
- Retains at most 400 append-only messages and uses the shared StatusStream batched renderer; important lifecycle/error messages are discarded only after ordinary entries.
- Completion updates the console with the new run link; failure surfaces the status log + stacktrace panel.
- Auth failures (`401`/`403`, including stale session-tab cases) now trigger a reload/sign-in prompt instead of silently continuing with stale page state.
- Cancel uses `/rq-engine/api/canceljob/<job_id>` to request termination.

## Blueprint
Module: `wepppy/weppcloud/routes/fork_console/fork_console.py`

- Blueprint name: `fork`.
- Route:
  - `rq_fork_console`: renders the console template, parses optional `undisturbify` and `skip_wepp_runs_output` query params, and authorizes the run.

## RQ API
Module: `wepppy/microservices/rq_engine/fork_archive_routes.py`

- `fork` (POST): queues `fork_rq` for the source run.
  - Payload: form fields `undisturbify`, `skip_wepp_runs_output`, and optional `target_runid`.
  - Validates permissions (run owners, admin users, public runs, or ownerless runs).
  - Session tokens that cannot resolve to an authenticated user are treated as anonymous requests (public-run checks + CAPTCHA required).
  - Allocates a new run ID via `awesome_codename` when no target is supplied.
  - Registers the new run in the user database when owner/user context is available (authenticated `user` and authenticated `session` token classes).
  - Responds with `{ job_id, new_runid, undisturbify, skip_wepp_runs_output }`.

## RQ Jobs
Module: `wepppy/rq/project_rq.py`

- `fork_rq(runid, new_runid, undisturbify, skip_wepp_runs_output)`:
  - Uses `rsync -a --stats` to clone the run directory without publishing per-file or per-progress output.
  - Publishes copy stage transitions, a replaceable elapsed-time heartbeat every 10 seconds, and bounded final summary/error tails to `<runid>:fork`.
  - When `skip_wepp_runs_output=True` (or when `undisturbify=True`), excludes `wepp/runs` and `wepp/output` from content copy, then creates those directories in the destination run.
  - Rewrites root `.nodb` paths, clears copied `_run_group`/`_group_name`
    identity for the interactive destination, removes copied Batch Runner
    `run_metadata.json`, and clears locks, `READONLY`, and `PUBLIC` markers.
  - When `undisturbify=True`, clears active SBS metadata without deleting copied SBS rasters, rebuilds landuse/soils, and enqueues WEPP; completion is emitted by
    `_finish_fork_rq` after WEPP finishes.
  - Emits `FORK_COMPLETE` on success and `FORK_FAILED` on failure.
- `_finish_fork_rq(runid)`: publishes the final completion trigger once dependent jobs finish.

## Fork Identity Compatibility and Regression Plan

An interactive destination fork must not retain batch-run identity from its source. For
each root-level `.nodb` payload, the destination contract requires `_run_group` and
`_group_name` to be absent or null even when the source is a Batch Runner leaf. Child
workspaces under `_pups/` are outside this normalization contract because they retain
their own orchestration identity. A copied `run_metadata.json` that identifies a batch
leaf is source execution metadata, not destination state, and must not remain active in
the interactive fork.

Compatibility is additive for ordinary forks: payloads with no batch identity remain
unchanged. Repair tooling must be dry-run-first, reject non-batch group identities,
validate an operator-supplied batch name when provided, create timestamped backups
before writing, update files atomically, and clear the destination's NoDb cache after a
successful repair. Source IDs, every root controller, and copied batch metadata must
name the same batch; incomplete or conflicting metadata fails before the first write.
If a later write fails, already-published root changes are restored atomically. If file
repair succeeds but cache invalidation fails, operators retry only cache invalidation
from the prepared, hash-verified backup manifest. This preserves model inputs and
outputs while changing only stale orchestration identity and copied batch execution
metadata.

Regression coverage must demonstrate that dry-run mode is non-mutating, apply mode
clears batch identity across root controllers, `_pups/` is untouched, mismatched group
identity fails before any write, batch `run_metadata.json` is backed up and removed,
and an already-repaired run is an idempotent no-op. The production acceptance check is
that `Ash.run_group` is unset and the ash route proceeds to WATAR enqueue rather than
returning the Batch Runner input-only response.

The alternative of changing only `ash.nodb` is rejected because the copied batch
identity affects other interactive controllers. Treating a primary-run URL as
authoritative while ignoring serialized group identity is also rejected because batch
leaf controllers depend on that identity inside their native Batch Runner context.

## Additional Details
- Status messages and triggers are published on the source run channel `<runid>:fork`.
- Fork completion is signaled by both StatusStream and polling. `/jobstatus/<job_id>` is authoritative; stream triggers accelerate reconciliation and guarded handlers prevent duplicate terminal flows.
- The new run ID is surfaced via both the status panel link and the console action panel.
- Operational thresholds and rationale are recorded in `docs/adrs/ADR-0021-fork-console-status-backpressure-thresholds.md`.
