# Harden Fork Console Status Backpressure and Recovery

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, a user can leave a large fork running in a background tab without returning to a console that spends minutes draining obsolete rsync output. The console still receives a WebSocket terminal signal and independently polls RQ, but `/jobstatus/<job_id>` is the only authority that declares success or failure. A reload or resumed tab restores the tracked fork, fetches current status immediately, and shows a bounded, responsive log.

The observable proof is a fork helper test that generates many process-output lines without publishing them, browser tests that exercise stream-trigger confirmation and reload/resume recovery, regenerated frontend assets, and all repository-standard focused gates passing.

## Progress

- [x] (2026-07-15 17:15 UTC) Captured production evidence and confirmed the existing deployed hybrid completion behavior.
- [x] (2026-07-15 17:15 UTC) Created the work package, tracker, active ExecPlan, ADR, and security-review scaffold.
- [x] (2026-07-15 17:24 UTC) Implemented bounded rsync stage/heartbeat/summary telemetry and focused Python tests.
- [x] (2026-07-15 17:24 UTC) Implemented authoritative completion, batched rendering, bounded important-message retention, visibility/focus recovery, session rehydration, and idle stream disconnection.
- [x] (2026-07-15 17:24 UTC) Added focused JavaScript/template tests and rebuilt generated assets.
- [x] (2026-07-15 17:24 UTC) Updated authoritative docs and controller helper docs.
- [x] (2026-07-15 17:32 UTC) Ran targeted and broad validation gates; recorded unrelated shared-worktree blockers.
- [x] (2026-07-15 17:32 UTC) Completed code, QA, and security reviews; closed the package and tracker.

## Surprises & Discoveries

- Observation: Production already had a two-second `/jobstatus/<job_id>` fallback, so the incident was not caused by missing polling.
  Evidence: Deployed `controllers-gl.js` contained `DEFAULT_POLL_INTERVAL_MS = 2000`, terminal dispatch, and stream disconnection logic.
- Observation: StatusStream rewrites the full retained log after every message, while fork rsync publishes each stdout line.
  Evidence: `status_stream.js::appendMessage` calls `setLogContent()` for every message; `project_rq_fork.py::_run_rsync_with_live_output` publishes every drained queue line.
- Observation: Redis Pub/Sub has no replay, and status2 has no browser-visibility gate.
  Evidence: `services/status2/internal/server/server.go` forwards received Pub/Sub payloads directly per connection.
- Observation: A first review of session restoration found that a stored destination run ID must never flow through HTML construction.
  Evidence: The implementation now uses `createTextNode`, `textContent`, and `encodeURIComponent`; a malicious-storage regression test proves no element injection.
- Observation: Repository-wide Python gates were not independently runnable in the shared worktree.
  Evidence: Pytest collection fails in the unrelated interchange refactor because `WAT_OPTIONAL_COLUMN_NAMES` is undefined; broad-exception enforcement reports additions only in those unrelated files while `project_rq_fork.py` has delta zero.

## Decision Log

- Decision: Preserve WebSocket and polling completion paths, but convert terminal stream triggers into immediate status-confirmation requests.
  Rationale: This retains reliability when either signal is delayed while preventing ephemeral or shared-channel messages from authoritatively terminating the UI.
  Date/Author: 2026-07-15 17:15 UTC / WEPPpy requesting maintainer and Codex.
- Decision: Suppress raw rsync filename/progress output and use bounded heartbeat plus final summary/error tails.
  Rationale: Users need evidence of activity and actionable failures, not every copied path.
  Date/Author: 2026-07-15 17:15 UTC / WEPPpy requesting maintainer and Codex.
- Decision: Persist only non-sensitive fork tracking fields in `sessionStorage`.
  Rationale: Same-tab reload recovery requires job and destination identifiers; tokens and authorization material are neither needed nor safe to persist.
  Date/Author: 2026-07-15 17:15 UTC / Codex.
- Decision: Keep the existing shared channel contract and queue graph unchanged.
  Rationale: Idle disconnection and authoritative job polling solve the confirmed incident without broadening the change into queue/channel architecture.
  Date/Author: 2026-07-15 17:32 UTC / Codex.

## Outcomes & Retrospective

Delivered all requested behaviors. Fork copies no longer publish raw rsync paths or progress lines; they emit bounded stage transitions, ten-second heartbeats, final statistics, and at most 200 lines from each diagnostic tail. StatusStream batches DOM rendering every 100 milliseconds, defers hidden rendering, caps the fork log at 400 entries, and preferentially retains lifecycle/error records. The fork console keeps WebSocket and polling signals, but only poll-origin terminal status changes the UI; it restores jobs from identifier-only session storage, reconciles on visibility/focus/pageshow, and does not connect while idle.

Validation passed for 10 focused worker tests, 3 template/generated-StatusStream tests, frontend lint, all 85 frontend suites and 629 tests, documentation lint, generated-controller parity, and `git diff --check`. The repository-wide Python sanity and broad-exception gates were attempted and are blocked by unrelated WEPPpyo3 interchange edits in the shared worktree; package code itself introduces no broad catch. Separate code, QA, and security reviews have no unresolved package findings.

No production deployment was performed. The remaining operational action is a separately authorized wepp1 deployment followed by the ADR's 14-day observation window through 2026-07-29.

## Context and Orientation

The fork API enqueues `wepppy.rq.project_rq.fork_rq`. That job delegates the copy to `wepppy/rq/project_rq_fork.py::prepare_fork_run`, which currently invokes `rsync -av --progress` and publishes every stdout/stderr line through `StatusMessenger` on `<source-runid>:fork`.

The browser page loads `wepppy/weppcloud/static/js/fork_console.js`. After submission it stores the returned job ID only in memory, connects `StatusStream` to the source-run channel, and asks a `controlBase` instance to poll `/rq-engine/api/jobstatus/<job_id>`. The page also connects to the fork channel immediately on initial load, even when no job is tracked.

`wepppy/weppcloud/controllers_js/status_stream.js` is the source for both the generated section of `controllers-gl.js` and the standalone `wepppy/weppcloud/static/js/status_stream.js`. It retains messages in an array and currently joins/replaces the full log text after every received frame. Changes to that source require running `python wepppy/weppcloud/controllers_js/build_controllers_js.py`.

Primary tests are `tests/rq/test_project_rq_fork.py`, `wepppy/weppcloud/controllers_js/__tests__/console_smoke.test.js`, and `tests/weppcloud/controllers_js/status_stream_test.js`. New tests must use existing test locations and repository markers where applicable.

## Plan of Work

First change the worker helper. Remove `-v` and `--progress` from the rsync command, request final statistics, drain stdout/stderr concurrently into bounded tails, and publish a replaceable heartbeat marker while the subprocess remains active. Publish one bounded final summary on success. On failure, publish and raise an explicit error containing bounded stdout/stderr tails. Preserve list-based `Popen` invocation, the sanitized environment, return-code enforcement, and all fork data behavior.

Next change StatusStream. Retain the existing public `attach`, `append`, trigger, stacktrace, and connection behavior. Store message records with importance metadata, trim ordinary entries before lifecycle/error entries when the configured limit is exceeded, and schedule at most one DOM flush per batching interval. Do not update hidden-page log DOM; flush when visible again. Continue dispatching append and trigger events as messages arrive so lifecycle consumers remain responsive.

Then change the fork console. Add a dedicated live-progress node. Format heartbeat-marker messages into replace-in-place progress text and suppress them from the append-only log. Stop the unconditional initial stream connection. On successful submission, store `{runId, config, jobId, newRunId}` in `sessionStorage`, connect the stream, and start polling. On initialization, restore a valid same-run record and resume the same behavior. Clear storage at terminal status. Add `visibilitychange`, `focus`, and `pageshow` reconciliation that immediately asks `controlBase` for the tracked job status. Stream `FORK_COMPLETE` and `FORK_FAILED` triggers request status reconciliation; poll-origin terminal events perform the existing completion/failure UI transition.

Finally add regression tests, rebuild generated assets, update the authoritative forking and controller helper docs, run validation, conduct separate code/QA/security review passes, disposition findings, and close the work package.

## Concrete Steps

Work from `/home/workdir/wepppy`.

1. Edit `wepppy/rq/project_rq_fork.py` and `tests/rq/test_project_rq_fork.py`; run `wctl run-pytest tests/rq/test_project_rq_fork.py`.
2. Edit `wepppy/weppcloud/controllers_js/status_stream.js`, `wepppy/weppcloud/static/js/fork_console.js`, and the fork-console control template; extend focused JavaScript tests.
3. Run focused frontend tests, then `python wepppy/weppcloud/controllers_js/build_controllers_js.py` and verify generated asset parity.
4. Update `docs/ui-docs/weppcloud-project-forking.md`, `wepppy/weppcloud/controllers_js/README.md`, this ExecPlan, the package tracker, and review artifacts.
5. Run `wctl run-npm lint`, `wctl run-npm test`, targeted pytest, `wctl run-pytest tests --maxfail=1`, changed-file broad-exception enforcement, and scoped docs lint.

## Validation and Acceptance

The worker tests must prove that `_build_fork_rsync_cmd` has no verbose/progress flags, heartbeat messages are emitted while a fake process remains active, large stdout/stderr sequences do not become status-message sequences, final summaries are bounded, and nonzero exit status raises an explicit bounded error.

The frontend tests must prove that StatusStream batches DOM writes, bounds retention while preferring important lifecycle/error messages, suppresses hidden-page rendering until visibility returns, and retains trigger dispatch. Fork-console tests must prove no idle stream attach, submission storage, reload restoration, immediate resume reconciliation, heartbeat replacement, and authoritative poll confirmation after either terminal stream trigger.

Generated `controllers-gl.js` and standalone `status_stream.js` must contain the source changes. Existing controller and fork-console tests must remain green. Documentation lint must pass for all changed Markdown files.

## Idempotence and Recovery

The implementation changes no persisted run data or API payload keys. Session storage is scoped by source run and config and is cleared on terminal state; invalid JSON is removed explicitly. Rebuilding frontend bundles is deterministic and safe to repeat.

If the worker telemetry change fails tests, restore the prior helper implementation with a targeted patch, not a destructive git reset. If shared StatusStream changes cause unrelated controller failures, keep the fork-specific formatter/recovery work and narrow batching to an opt-in option while preserving the same acceptance behavior.

## Artifacts and Notes

- Package: `docs/work-packages/20260715_fork_console_status_backpressure/`
- Security review: `artifacts/20260715_security_review.md`
- Code review: `artifacts/20260715_code_review.md`
- QA review: `artifacts/20260715_qa_review.md`
- ADR: `docs/adrs/ADR-0021-fork-console-status-backpressure-thresholds.md`

## Interfaces and Dependencies

No new external dependency is allowed. Rsync remains invoked with a list argument and `shell=False` behavior through `subprocess.Popen`. Status messages remain strings on the existing `<runid>:fork` channel. A heartbeat string must use a stable fork-specific prefix that the frontend can recognize and replace rather than append. The existing `StatusStream.attach(options)` interface may gain backward-compatible batching and importance options; existing callers that omit them must continue to work. Session storage must contain identifiers only and must never contain bearer tokens, CAP tokens, or user data.
