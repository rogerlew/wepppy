# Roads NoDb Inslope E2E Closeout Rollback Validation

**Date**: 2026-04-10
**Run**: `clogging-starch` (`/wc1/runs/cl/clogging-starch`)
**Purpose**: Capture explicit rollback evidence required to close the package lifecycle.

## 1. Mod Disable / Re-Enable Rollback

Command:

```bash
wctl exec weppcloud python - <<'PY'
# calls _disable_mod_for_run(..., "roads") and _enable_mod_for_run(..., "roads")
# verifies roads.nodb backup/restore and hash parity after re-enable
PY
```

Observed results:
- `changed_disable=true`
- `mods_contains_roads_after_disable=false`
- `roads.nodb` removed after disable, `roads.bak` created
- `changed_enable=true`
- `mods_contains_roads_after_enable=true`
- `roads.nodb` restored and hash matched pre-disable content (`roads_nodb_hash_restored=true`)

## 2. Artifact Isolation and Queue Rollback State

Command:

```bash
wctl exec weppcloud python - <<'PY'
# inspects Roads summary/status, report resource relpaths, active roads job, and lock keys
PY
```

Observed results:
- `roads_status=completed`
- `required_relpaths_all_under_wepp_roads=true` (`required_relpaths_count=9`)
- `active_roads_job=null`
- `roads:submit_lock:clogging-starch=null`
- `roads:runtime_lock:clogging-starch=null`
- Noted expected derived cache files under `wepp/reports/cache/*roads*` outside `wepp/roads/*`

## 3. Targeted Regression Backstop

Commands and outcomes:

```bash
wctl run-pytest tests/weppcloud/routes/test_project_bp.py -k "set_mod_roads_allows_when_wbt_backend or set_mod_disables_module_when_no_guards" --maxfail=1
# 2 passed

wctl run-pytest tests/rq/test_roads_rq.py --maxfail=1
# 4 passed

wctl run-pytest tests/nodb/mods/test_roads_controller.py -k "test_regenerate_roads_report_resources_uses_roads_scope_outputs" --maxfail=1
# 1 passed
```

## Closeout Decision

Rollback validation requirements are satisfied for:
- mod disable/re-enable recovery,
- roads artifact isolation contract, and
- queue rollback hygiene.

Package is eligible for closure.
