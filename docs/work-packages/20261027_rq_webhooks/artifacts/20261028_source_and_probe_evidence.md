# RQ webhook source inventory and isolated probes

Date: 2026-10-28. Starting HEAD: `dd4e5381ba4e3fd66e82c0e14e8d82faa174ff47`.
No branch switch, commit, application source edit, live Redis access or stack restart.

## Starting worktree

Preexisting modifications: PROJECT_TRACKER.md, docs/dev-notes/rq-webhooks-contract-draft.md,
and this package's package.md, tracker.md, decision_register.md and active ExecPlan.
Preexisting untracked files: hierarchy review, acceptance matrix and kickoff prompt.
These were preserved and read as the handoff; no unrelated changes were reverted.

## Source boundaries

| Boundary | Observed source | Implication |
| --- | --- | --- |
| Shared enqueue | `wepppy/rq/auth_actor.py:install_rq_auth_actor_hook` wraps enqueue and enqueue_call | Actor propagation is not universal publication/lineage coverage |
| Caller transactions | RQ Queue.enqueue_call with caller pipeline | Returned Job is not proof of publication; closure must await commit/abort |
| Bulk/direct | RQ Queue.enqueue_many, enqueue_job, _enqueue_job; `geneva_routes.py` directly saves/registers jobs | All require coverage or callback admission exclusion; outer wrapper alone insufficient |
| Culvert hierarchy | `culvert_rq_pipeline.py:_enqueue`, `_record_parent_meta` | Child visible before parent metadata; post-publication enumeration can miss it |
| WEPP hierarchy | `wepp_rq_pipeline.py:_enqueue` | Planned child ID saved before enqueue; missing job may mean orphan intent, not success |
| Polling | `job_info.py:recursive_get_job_details`, get_wepppy_rq_job_status | Missing jobs represented as None, descendants project parent failure; unsuitable terminal predicate |
| Failure-tolerant release | `job_dependencies.py:release_deferred_job_if_ready` | Actual FAILED differs from logically blocked DEFERRED; stopped exception requires explicit handler |
| Worker lifecycle | `rq_worker.py:perform_job`, handle_job_failure, handle_job_success, monitor_work_horse | Need workhorse plus supervisor evidence; current status signals are not closure records |
| Callbacks | RQ worker/base.py executes success callback before success handling; failure callback before failure handling; fork_failure callback and supervisor fallback | Callback publication and supervisor death paths both matter |
| Cancellation | `cancel_job.py:_cancel_job_recursive_unlocked` and worker kill/monitor paths | Cancel status is not execution-exit evidence; traversal continues below terminal parents |
| Admission/recovery | `wepp_routes.py:_handle_run_wepp_request`, `culvert_routes.py:_enqueue_culvert_job`, submission_recovery.py | Existing locks/receipts must remain; initial culvert batch creation needs dedup identity after lost response |
| Detached work | run_catalog_rq.py, wmesque_rq.py; query-catalog special handling in job_info | Explicit server-only detached classification, not inferred from job name by evaluator |
| Exposure | profile_recorder.py sensitive-key list lacks webhook_url; recorder requestMeta can retain form/JSON values | Redact before capture, omit callback/key during playback; audit all log/description surfaces |

Scope inventory is sufficient to reject wrapper-only reuse, not proof of exhaustive
producer coverage. Activation still requires an executable inventory of every
reachable producer/callback in the admitted workflows, including alternate workers.

## Reproducible real Redis probe

Command from repository root:

    PYTHONPATH=. .venv/bin/python docs/work-packages/20261027_rq_webhooks/artifacts/probes/settlement_probe.py

[Probe source](probes/settlement_probe.py) starts Redis on a disposable mode-700 Unix
socket with TCP disabled, no configured application connection and no persistence.
It terminates its own process and removes its temporary directory. It runs real
RQ SimpleWorker/dependency handling. [Retained output](probes/settlement_probe.json):
RQ 2.12.0, redis-py 6.2.0, Redis server 7.0.15; all assertions passed. Initial probe
used Python `int` as task, rejected by RQ's function resolver; changed fixture to
importable `json.loads` and reran successfully. No production defect implied.

Confirmed: enqueue_call propagates actor while enqueue_many/enqueue_job do not;
caller pipeline returns before publication; post-enqueue parent registration has
an observable gap; A failed -> B strict -> C allow_failure leaves B/C deferred,
while directly failure-tolerant D finishes. Stopped observer remains deferred until
existing release helper runs; canceled prerequisite remains blocking. WATCH rejects
a revision changed before event commit. This last probe validates Redis mechanics,
not a complete webhook atomic protocol or concurrent writer coverage.

## Candidate comparison and escalation

Existing polling plus enqueue wrapper is the smallest reuse candidate. It misses
bulk/direct paths and has publication gaps demonstrated above; status projection
cannot supply producer closure. Escalation needed: minimal server-owned publication
and closure receipts, shared bounded hooks and independent graph evaluation.

| Execution option | Assessment | Operational/recovery cost |
| --- | --- | --- |
| Native/inline HTTP in computation workers | Rejected by accepted isolation requirement; synchronous RQ webhook path is excluded | Receiver holds compute capacity; timeout alone cannot fix placement |
| Dedicated RQ delivery queue/worker | Feasible candidate, not selected | Adds queue, delivery job TTL/retry semantics and a separate evaluator placement |
| Independent bounded dispatcher, same Redis namespace | Recommended for approval | One process/service lifecycle; indexed due work, fenced claims, killable HTTP subprocesses; preserves existing queue list |
| New durable datastore/broker | No demonstrated need under explicit Redis-loss limits | New transaction/backup/recovery boundary; not proposed |

Topology recommendation is not a benchmark claim. No dispatcher or HTTP sender has
been implemented, so no controlled receiver, total-deadline, concurrency, producer
closure, throughput or generated-artifact acceptance is claimed. Those are explicit
implementation/activation gates. No new external dependency is recommended.

## Proposed implementation interfaces after checkpoint

New `wepppy/rq/webhook_tracking.py`: bounded admission/publication/closure receipts;
`webhook_settlement.py`: paginated generic evaluator and conditional event commit;
`webhook_dispatcher.py`: due-work scheduling, fenced attempt claims and operator
controls; `webhook_http.py`: killable deadline and pinned TLS transport using existing
Python facilities. `rq_engine/webhooks.py`: shared field validation, route support
and idempotency response binding. These are intended boundaries, not existing files.

Instrument existing shared enqueue and worker lifecycle paths; do not replace task
functions or domain exception semantics. Exact RQ lower-level hooks must be validated
against bulk/deferred/caller transactions before activation. New unit/integration
suites should live in `tests/rq/test_webhook_*` and
`tests/microservices/test_rq_engine_webhooks.py`; real Redis/process/HTTP fixtures
must test the actual persistence and security boundaries. Model artifacts remain
unchanged; parity acceptance is still required.
