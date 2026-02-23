# Mini Work Package: Project-Config NoDir Policy
Status: Implemented
Last Updated: 2026-02-23
Primary Areas: `wepppy/nodb/configs/_defaults.toml`, `wepppy/microservices/rq_engine/project_routes.py`, `wepppy/microservices/rq_engine/upload_huc_fire_routes.py`, `wepppy/weppcloud/routes/test_bp.py`, `tests/microservices/test_rq_engine_project_routes.py`, `tests/microservices/test_rq_engine_upload_huc_fire_routes.py`, `tests/weppcloud/routes/test_test_bp.py`, `docs/configuration-reference.md`

## Objective
Allow project configs to opt in to default NoDir behavior for new runs, with NoDir disabled by default unless both global and config gates are enabled.

## Why This Is Needed
Current new-run creation paths always call `enable_default_archive_roots(wd)` after `Ron(wd, cfg)`. This forces marker seeding for all configs:
- `wepppy/microservices/rq_engine/project_routes.py`
- `wepppy/microservices/rq_engine/upload_huc_fire_routes.py`
- `wepppy/weppcloud/routes/test_bp.py`

That means NoDir policy is currently global (`WEPP_NODIR_DEFAULT_NEW_RUNS`) or hardcoded, but not config-specific. Desired behavior is stricter: global gate on plus per-config opt-in.

## Current-State Findings
1. NoDir default marker mechanics are already run-local:
   - marker path: `WD/.nodir/default_archive_roots.json`
   - written by: `wepppy/nodir/mutations.py:enable_default_archive_roots`
2. Global kill switch already exists:
   - env var: `WEPP_NODIR_DEFAULT_NEW_RUNS`
   - `0/false/no/off` prevents marker writes.
3. Config parsing already supports new keys in `[nodb]`:
   - `NoDbBase.config_get_bool("nodb", "<key>", default)`
   - create endpoints already pass config overrides as query-style `section:option=value` in `cfg`.

## Proposed Contract
Add a config-level boolean gate:

```ini
[nodb]
apply_nodir = false
```

Behavior:
1. If `WEPP_NODIR_DEFAULT_NEW_RUNS=0` (or equivalent false token), do not seed `WD/.nodir/default_archive_roots.json`, regardless of config.
2. If global `WEPP_NODIR_DEFAULT_NEW_RUNS` is enabled, seed marker only when `apply_nodir = true` for that config.
3. Missing `apply_nodir` is treated as `false` (opt-in required).

Scope note:
- This package controls whether NoDir defaults are seeded for new runs.
- It does not change NoDir mutation/projection contracts after run creation.

## Design Details
### Config Key
- Add `apply_nodir = false` under `[nodb]` in `wepppy/nodb/configs/_defaults.toml`.
- Projects opt in in specific `.cfg` files with `apply_nodir = true`.

### Create-Flow Wiring
In each run-creation surface:
1. Keep `Ron(wd, cfg)` unchanged.
2. Read config policy from instantiated Ron config parser:
   - `ron.config_get_bool("nodb", "apply_nodir", False)`
3. Keep existing global env gate behavior in `enable_default_archive_roots`.
4. Call `enable_default_archive_roots(wd)` only when config policy is true.

Target files:
- `wepppy/microservices/rq_engine/project_routes.py`
- `wepppy/microservices/rq_engine/upload_huc_fire_routes.py`
- `wepppy/weppcloud/routes/test_bp.py`

## Test Plan
1. Add baseline-off assertions:
   - Create flows without config opt-in should not create marker.
2. Add opt-in assertions:
   - Create run with `nodb:apply_nodir=true` override (where endpoint supports overrides), assert marker exists.
   - Add one fixed-config opt-in test (fixture cfg with `[nodb] apply_nodir=true`) for fixed-config create path.
3. Keep global env-gate assertions:
   - Even with `apply_nodir=true`, `WEPP_NODIR_DEFAULT_NEW_RUNS=0` prevents marker creation.
4. Ensure no regression in NoDir mutation behavior tests:
   - `tests/nodir/test_mutations.py`

## Validation Commands
From `/workdir/wepppy`:

```bash
wctl run-pytest tests/microservices/test_rq_engine_project_routes.py tests/microservices/test_rq_engine_upload_huc_fire_routes.py tests/weppcloud/routes/test_test_bp.py --maxfail=1
wctl run-pytest tests/nodir/test_mutations.py --maxfail=1
wctl doc-lint --path docs/mini-work-packages/20260223_project_config_nodir_policy.md
```

## Rollout and Compatibility
- Default behavior changes to marker-off for configs that do not opt in.
- Initial rollout keeps all existing configs at default-off (no config opt-ins added).
- Configs that should retain default NoDir behavior can set `[nodb] apply_nodir=true` in a future targeted change.
- Global rollback remains `WEPP_NODIR_DEFAULT_NEW_RUNS=0`.

## Open Questions
1. Do we also want a future per-config root subset key (for example `default_archive_roots=[...]`), or keep this package strictly boolean?
