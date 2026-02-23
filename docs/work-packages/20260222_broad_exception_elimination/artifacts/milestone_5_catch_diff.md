# Milestone 5 Catch Diff

## Scope

Milestone 5 WEPPcloud route cleanup batch A converted bare exception handlers to explicit `except Exception` boundaries in high-traffic route handlers:

- `wepppy/weppcloud/routes/user.py`
- `wepppy/weppcloud/routes/nodb_api/wepp_bp.py`

Regression tests added/updated:
- `tests/weppcloud/routes/test_wepp_bp.py`

## Catch Count Delta (Touched Files)

Checker source: `python3 tools/check_broad_exceptions.py --json`

| File | Before Findings | After Findings | Delta |
|------|----------------:|---------------:|------:|
| `wepppy/weppcloud/routes/user.py` | 11 | 11 | 0 |
| `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` | 26 | 26 | 0 |
| **Total (touched files)** | **37** | **37** | **0** |

Bare-catch normalization (touched files):
- Before: `12` bare catches (`6` in `user.py`, `6` in `wepp_bp.py`).
- After: `0` bare catches.

Global checker summary:
- Before Milestone 5 (from Milestone 4 snapshot): `1105` unsuppressed broad catches (`bare=94`, `except-Exception=1011`).
- After Milestone 5: `1105` unsuppressed broad catches (`bare=82`, `except-Exception=1023`).
- Net total reduction: `0` (all changes were bare->explicit-Exception normalization).

## Commands Run

- `python3 tools/check_broad_exceptions.py wepppy/weppcloud/routes/user.py wepppy/weppcloud/routes/nodb_api/wepp_bp.py` -> pass (report generated; non-zero exit expected while findings exist).
- `python3 tools/check_broad_exceptions.py wepppy services` -> pass (report generated; non-zero exit expected while findings exist).
- `python3 -m py_compile wepppy/weppcloud/routes/user.py wepppy/weppcloud/routes/nodb_api/wepp_bp.py tests/weppcloud/routes/test_wepp_bp.py` -> pass.
- `wctl run-pytest tests/weppcloud/routes/test_exception_logging_routes.py tests/weppcloud/routes/test_wepp_bp.py --maxfail=1` -> pass (`14 passed`).
- `wctl run-pytest tests/weppcloud/routes/test_user_profile_token.py tests/weppcloud/routes/test_user_runs_admin_scope.py --maxfail=1` -> pass (`12 passed`).

## Residual Risks / Deferred Items

- Route boundaries now avoid catching `BaseException` subclasses, but still use broad `except Exception` wrappers in many endpoints; deeper narrowing by exception type is deferred.
- Potential `HTTPException` masking remains in some handlers with wide `try` scopes and `except Exception` blocks; defer route-by-route classification in later batches.
