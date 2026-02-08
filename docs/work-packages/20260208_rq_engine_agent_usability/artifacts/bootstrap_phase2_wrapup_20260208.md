# Bootstrap Phase 2 Wrap-Up Artifact (2026-02-08)

## Source
Phase 2 production-readiness review outcomes for Bootstrap + rq-engine integration.

## Implemented Remediations
- Canonical run-path resolution using `get_wd(..., prefer_active=False)` for
  bootstrap mutation routes and enable enqueue paths.
- Flask bootstrap status-code hardening with explicit `400/404/409/500` handling
  and generic internal error payloads.
- Admin/Root parity enforced across web helper and rq-engine authorization logic.
- rq-engine bootstrap routes sanitize unexpected failures (no traceback payload
  leakage to clients).
- `bootstrap_disabled` blocks push/pull and mint/enable; read/checkout remain
  available.
- Enable lock and dedupe TTLs scale with queue timeout
  (`max(configured_ttl, RQ timeout + 300)`).
- Git lock protection added around WEPP/SWAT auto-commit mutation paths.
- Production compose defaults hardened for JWT and D-Tale secret handling.

## Documentation Updates Confirmed
- `docs/weppcloud-bootstrap-spec.md` aligned with current behavior and testing.
- `wepppy/rq/job-dependencies-catalog.md` updated for bootstrap and no-prep
  wiring.

## Regression Coverage Confirmed
- rq-engine bootstrap auth negative paths (scope, expiry, audience, revocation).
- Flask bootstrap route regressions (status codes and canonical wd behavior).
- Enable-job TTL behavior.
- WEPP/SWAT auto-commit lock behavior.
- Pre-receive edge policy cases (symlink/submodule/rename-copy/delete paths).

## Verification Run
- Command:
  - `wctl run-pytest tests/weppcloud/routes/test_bootstrap_bp.py tests/weppcloud/routes/test_bootstrap_auth_integration.py tests/microservices/test_rq_engine_bootstrap_routes.py tests/rq/test_bootstrap_enable_rq.py tests/weppcloud/bootstrap/test_enable_jobs.py tests/rq/test_bootstrap_autocommit_rq.py tests/weppcloud/bootstrap/test_pre_receive.py`
- Result:
  - `60 passed`

## Residual Risk Notes
- Read-only job polling remains open by policy; risk acceptance currently relies
  on UUID4 job ID entropy and non-mutating semantics.
- No destructive bootstrap-init timing measurement was run on
  `/wc1/runs/fa/fast-paced-blastoff` because the run currently lacks `.git` and
  `wepp/runs` trees.
