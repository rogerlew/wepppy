# Optional Discord import restoration

Starting revision: `0e331f5e2`. User direction on 2026-10-08: “why is discord a hard requirement. it shouldn't be”.

## Classification and scope

Conformance repair of expected absent optional state under [contract-first valid-state requirements](../../../standards/contract-first-change-standard.md#valid-state-and-user-experience-gate-required). Optional-package handling already permits operation without Discord; core `wepp.py` also handles missing/unreadable credential files. Four RQ import sites omit that handling, preventing unrelated fork tasks from importing.

Apply the existing core WEPP handling to `wepp_rq_stage_finalize.py`, `wepp_rq.py`, `omni_rq.py`, and `batch_rq.py`: catch `FileNotFoundError` and `PermissionError`, log disabled notifications, and retain `send_discord_message=None`. The missing-package behavior and configured sender remain intact. Unexpected import/programming failures still propagate. Delivery-time failures and empty/invalid credentials are outside this import-only repair; do not claim general notification transport isolation. No queue, completion-event, authentication, or model-parameter contract changes.

## Regression and compatibility

Exercise the project-task import chain in a fresh subprocess with an optional client that opens an actually absent credential file. Separately cover unreadable credentials and a configured sender; never transmit a real notification. No persisted schemas or scientific inputs change. The missing-file test reproduced the production failure before the patch.

Run focused RQ regression tests and the required full suite, then obtain independent correctness review. Deployment validation must import tasks in the affected worker without a Discord token and successfully fork the baseline before claiming incident resolution. Do not manufacture a credential or change deployment identity/permissions.

## Results

Pre-fix: missing-token regression fails at the same `wepp_rq_stage_finalize` import as both production fork jobs.

Post-fix, 2026-10-09 00:29 UTC: focused RQ validation passes (54 passed, 26 skipped); the three isolated import cases pass again after reusing the shared Redis stub inside subprocesses. Stub completeness, Markdown lint, and whitespace checks pass. Independent correctness review has no blocking findings; see [review](20261008_discord_import_review.md).

The required full-suite attempt stops after 10,284 passed and 126 skipped at `tests/weppcloud/test_run_catalog_postgres.py::test_marker_notification_latency_without_prior_sql_mirror[ttl]`: measured p95 overhead 61.1 ms exceeds its 50 ms limit. This unchanged TTL/catalog timing path does not execute the modified Discord imports in its timed loop. The isolated recheck also fails. No unrelated performance threshold or implementation was changed. Therefore full-suite green status is not claimed.

The fix is local and not deployed. Production worker import and successful calibration fork validation remain outstanding. No token was provisioned and no notifications were sent.
