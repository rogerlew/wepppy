# Correctness/Risk Review Findings

Date: 2026-02-24  
Reviewer: Codex (correctness/risk pass)

## Scope Reviewed

- `wepppy/weppcloud/configuration.py`
- `wepppy/weppcloud/app.py`
- `wepppy/weppcloud/templates/base_pure.htm`
- `wepppy/weppcloud/static/js/csrf_bootstrap.js`
- `wepppy/weppcloud/routes/_security/oauth.py`
- `wepppy/weppcloud/routes/bootstrap.py`
- `wepppy/weppcloud/routes/_run_context.py`
- `wepppy/microservices/rq_engine/session_routes.py`
- `wepppy/weppcloud/controllers_js/__tests__/csrf_bootstrap.test.js`
- `docs/standards/broad-exception-boundary-allowlist.md`
- `tests/microservices/test_rq_engine_session_routes.py`
- `tests/weppcloud/routes/test_csrf_rollout.py`
- CSRF contract + package artifacts

## Findings

| Severity | Finding | Disposition |
| --- | --- | --- |
| Medium | `rq_engine/session_routes.py` same-origin allow-list accepted `X-Forwarded-*` header aliases by default, creating header-spoofing risk when rq-engine is exposed directly. | Fixed: forwarded-origin aliases now require explicit opt-in (`RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS=true`); default path trusts request host and configured external aliases only. Added regression coverage for strict default and opt-in behavior. |
| Low | Re-importing global app after a test-local bootstrap blueprint registration triggered a run-context preprocessor assertion. | Fixed: `register_run_context_preprocessor` now short-circuits when already registered or when blueprint setup is finalized. |

## Missing Coverage Check

- Added explicit CSRF regression suite: `tests/weppcloud/routes/test_csrf_rollout.py`.
- Added rq-engine cookie-path same-origin regression tests in `tests/microservices/test_rq_engine_session_routes.py`.
- Added dedicated CSRF bootstrap Jest coverage: `wepppy/weppcloud/controllers_js/__tests__/csrf_bootstrap.test.js`.
- No missing blocking coverage identified for the implemented behavior.

## Conclusion

- No unresolved High-severity correctness findings.
- Package behavior is acceptable for rollout; forwarded-header spoofing exposure is now reduced by default-deny proxy alias handling.
