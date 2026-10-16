# Repository test-isolation follow-up

Status: open backlog, separated from WMesque M7 on 2026-10-16 by operator approval.
Owner: WEPPpy maintainers. No production behavior change is authorized by this item.

## Evidence and scope

[Run 38860272720](https://github.com/rogerlew/wepppy/actions/runs/38860272720)
passes stubtest, the full baseline (10,690 passed, 329 skipped), all five
unchanged-order repeats, and per-file test execution. The final state scan
reports 18 findings. These remain open; the run is not relabeled successful.

Sixteen files add `ASSET_VERSION=6a5f05572` through application initialization:

- `tests/microservices/test_rq_engine_fork_archive_routes.py`
- `tests/microservices/test_rq_engine_session_routes.py`
- `tests/microservices/test_rq_engine_upload_batch_runner_routes.py`
- `tests/rq/test_project_rq_delete_run.py`
- `tests/weppcloud/routes/test_admin_usermod_contract.py`
- `tests/weppcloud/routes/test_blueprint_registration.py`
- `tests/weppcloud/routes/test_bootstrap_auth_integration.py`
- `tests/weppcloud/routes/test_bootstrap_bp.py`
- `tests/weppcloud/routes/test_feature_access_routes.py`
- `tests/weppcloud/routes/test_postfire_report_bp.py`
- `tests/weppcloud/routes/test_run_0_openet_admin_gate.py`
- `tests/weppcloud/routes/test_user_runs_admin_scope.py`
- `tests/weppcloud/test_run_catalog_postgres.py`
- `tests/weppcloud/test_run_catalog_reader.py`
- `tests/weppcloud/test_user_preferences.py`
- `tests/weppcloud/utils/test_helpers_authorize.py`

`tests/nodb/test_base_misc.py` leaves `tests.fake_mod` in `sys.modules`.
`tests/rq/test_fork_failure.py` leaves `RQ_JOB_ID` and `RQ_WORKER_ID` in the
environment. Classify initialization effects separately from actual fixture
leaks, restore test-owned state, and preserve the checker's replacement/mutation
negative controls. Do not broadly suppress environment or module findings.

## Bounded execution sequence

Start with actual execution of each affected group, not collection-only checks:

    wctl check-test-isolation tests/nodb/test_base_misc.py tests/rq/test_fork_failure.py --iterations 1 --max-workers 2 --json

Then run the sixteen app-importing files listed above as explicit targets using
the same one-iteration command. Reproduce in the isolated CI runtime where
Forest environment defaults hide additions. Require passing assertions and
`issues: []` for each repaired group. Fix fixtures before considering additional
checker exceptions; document narrow initialization rules if necessary.

After focused qualification, manually dispatch `test-isolation.yml` for complete
acceptance. It also runs weekly (Saturday 08:17 UTC). Do not use repeated
four-hour runs to discover the next known failure. Repetition count, scan rules,
assertions, and failure exits are unchanged; shuffled-order coverage remains
unproven until an actual plugin is evaluated and configured.

## Completion criteria

Close this item only after the affected-file execution/state checks and a fresh
exhaustive workflow pass. Retain run links and negative-control results in this
file. WMesque M7 is already accepted under its explicit revised scope; M8
recurring catalog synchronization remains disabled and outside this work item.
