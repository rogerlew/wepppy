# Final Validation Summary - 20260223 Bare Exception Zero

## Scanner Metrics

### No Allowlist (hard gate view)

- Baseline (`artifacts/baseline_no_allowlist.json`):
  - findings: `1099`
  - bare-except: `82`
  - except-Exception: `1017`
- Final (`artifacts/after_no_allowlist.json`):
  - findings: `1066`
  - bare-except: `0`
  - except-Exception: `1066`

### Allowlist Enabled (policy view)

- Baseline (`artifacts/baseline.json`):
  - findings: `1088`
  - bare-except: `82`
  - except-Exception: `1006`
  - allowlisted: `11`
- Final (`artifacts/after.json`):
  - findings: `1055`
  - bare-except: `0`
  - except-Exception: `1055`
  - allowlisted: `11`

## Required Gates

- `python3 tools/check_broad_exceptions.py --json --no-allowlist > /tmp/broad_no_allow.json`
  - Exit: `1` (expected when findings exist)
- `jq -e '.kinds["bare-except"] == 0' /tmp/broad_no_allow.json`
  - Exit: `0` (`true`)
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
  - Exit: `0`
  - Result: `PASS`
  - Net delta (changed files): `-38`

## Targeted Tests

- `wctl run-pytest tests/weppcloud/routes --maxfail=1`
  - First run: failed (contract regression in `mint_profile_token` message)
  - After fix: `228 passed`
- `wctl run-pytest tests/nodb --maxfail=1`
  - `495 passed, 3 skipped`
- `wctl run-pytest services/cao/test/services/test_inbox_service.py --maxfail=1`
  - `10 passed`
- `wctl run-pytest tests/nodb/test_base_unit.py tests/nodb/test_base_misc.py --maxfail=1`
  - `40 passed`

## Full Pre-Handoff Suite

- `wctl run-pytest tests --maxfail=1`
  - Run 1: `2057 passed, 29 skipped`
  - Run 2 (after final NoDb logging + allowlist alignment updates): `2057 passed, 29 skipped`

## Deferred File Contract Checks

- `wepppy/weppcloud/routes/user.py`
  - JWT config error message contract preserved (`error_factory(str(exc), 500)` for `JWTConfigurationError`)
  - Broad boundary allowlist entries aligned to per-run metadata helper boundaries (`_build_meta`, `_build_map_meta`)
- `services/cao/src/cli_agent_orchestrator/services/inbox_service.py`
  - Delivery failure path preserves re-raise behavior and FAILED status update.
  - No new broad-catch increases vs base.
