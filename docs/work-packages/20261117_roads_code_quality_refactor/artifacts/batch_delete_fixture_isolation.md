# Ordinary batch-deletion fixture isolation

The canonical baseline reproduction failed in
`test_delete_batch_rq_removes_workspace`: `_retention_delete_root` attempted to
place the test's disposable `/tmp/.../demo` directory beneath inherited `/wc1`.
The test already replaces controller lookup, cache/lock cleanup, job inventory
and status publication; only fresh pytest temporary storage was involved.
Baseline result: **one failed**, 10.11 seconds.

The sole source change is a module-local autouse fixture in
`tests/rq/test_batch_rq_delete_batch.py` that clears inherited retention ID/root
settings with `monkeypatch`. All five module cases represent ordinary workspaces;
there are no dedicated retention cases in this file. Production guards, deletion
logic and assertions remain unchanged. The complete canonical module now passes:
**five passed**, 9.79 seconds.

`batch_delete_fixture_receipt.json` retains baseline/candidate source hashes and
binds both guarded logs and JUnit results under `candidate_logs/`. Final source is
frozen for the v5 diagnostic; no other source files were changed in this task.

## Read-only RQ consumer inventory

This is an impact inventory, not additional failure proof. No listed file was
changed or executed by this follow-up inspection.

| Consumer | Observed fixture behavior |
| --- | --- |
| test_project_rq_delete_run.py | First two ordinary deletion tests use `_stub_delete_environment` without retention environment cleanup; possible same failure class, awaiting v5 evidence. Two dedicated retention tests explicitly configure their own ID/root and must preserve that coverage. |
| test_project_rq_fork.py | Ordinary fork helpers do not declare retention storage; canonical outside-storage behavior differs from the strict deletion helper. Await actual diagnostic results. |
| test_batch_rq_retry_selection.py | Deletion coverage asserts active-job rejection before cleanup; no demonstrated storage-boundary failure. |
| test_project_rq_archive.py; test_batch_outcome.py | Ordinary archive consumers use the already isolated `archive_rq_environment`. |
| test_vector_archive_recovery.py | Dedicated retention fixture explicitly restores ID/root and real ledger after ordinary archive setup. |
| test_vector_fork_retention.py; test_vector_retention_deletion.py | Dedicated fixtures explicitly declare temporary managed storage and unique identities; negative cases deliberately remove or replace settings. |
| test_rq212_lifecycle.py; test_webhook_tracking.py | Search matches concern job/result or principal retention, not vector storage lifecycle. |

Further edits are deferred until the complete maxfail-zero diagnostic supplies
actual remaining failures and source-stable evidence.
