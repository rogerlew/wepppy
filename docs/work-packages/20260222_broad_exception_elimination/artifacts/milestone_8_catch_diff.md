# Milestone 8 Catch Diff

## Scope

Milestone 8 deferred swallow-style hotspot closure:

- `wepppy/weppcloud/routes/user.py` (`_claim_names`, `_build_meta`, `_build_map_meta`)
- `services/cao/src/cli_agent_orchestrator/services/inbox_service.py` (`_has_idle_pattern`, provider import detection)

Regression tests added/updated:

- `tests/weppcloud/routes/test_user_profile_token.py`
- `tests/weppcloud/routes/test_user_runs_admin_scope.py`
- `services/cao/test/services/test_inbox_service.py`

## Catch Count Delta (Touched Files)

Comparison basis: post-Milestone 7 snapshot to post-Milestone 8 state (`--no-allowlist` for apples-to-apples catch totals).

| File | Before (M7) | After (M8) | Delta |
|------|------------:|-----------:|------:|
| `wepppy/weppcloud/routes/user.py` | 11 | 10 | -1 |
| `services/cao/src/cli_agent_orchestrator/services/inbox_service.py` | 5 | 2 | -3 |
| **Total (touched files)** | **16** | **12** | **-4** |

Global no-allowlist summary:

- Before Milestone 8 (from Milestone 7 summary): `1103` broad catches.
- After Milestone 8: `1099` broad catches.
- Net reduction in Milestone 8: `-4`.

Canonical allowlist update:

- Added `BEA-20260223-010` and `BEA-20260223-011` for deliberate per-run WEPPcloud list boundaries (`user.py` lines `497` and `515`).
- Current allowlist-suppressed global findings: `1088` (`allowlisted_count=11`).

## Commands Run

- `wctl run-pytest services/cao/test/services/test_inbox_service.py --maxfail=1` -> pass (`10 passed`).
- `wctl run-pytest tests/weppcloud/routes/test_user_profile_token.py tests/weppcloud/routes/test_user_runs_admin_scope.py --maxfail=1` -> pass (`17 passed`).
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` -> pass (`Result: PASS`, changed-file net delta `-28`).
- `wctl run-pytest tests --maxfail=1` -> pass (`2057 passed, 29 skipped`).

## Residual Risks / Deferred Items

- `_build_meta` and `_build_map_meta` intentionally retain broad per-run boundaries to prevent single-run workspace corruption from failing list endpoints; these are now explicit allowlisted boundaries with logging and regression coverage.
- `inbox_service` still has true boundary broad catches around send and watchdog callbacks (`services/cao/src/cli_agent_orchestrator/services/inbox_service.py:188`, `services/cao/src/cli_agent_orchestrator/services/inbox_service.py:222`); they are logged and not silent.
