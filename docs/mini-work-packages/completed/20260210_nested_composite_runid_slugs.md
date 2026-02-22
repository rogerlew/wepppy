# Mini Work Package: Nested Composite Runid Slugs For Batch + Omni (GL Dashboard)
Status: Implemented
Last Updated: 2026-02-10
See also: `docs/composite-runid-slugs.md`, `docs/mini-work-packages/20260209_gl_dashboard_batch_mode.md`
Primary Areas: `wepppy/weppcloud/utils/helpers.py`, `wepppy/weppcloud/routes/_run_context.py`, `wepppy/weppcloud/static/js/gl-dashboard/scenario/manager.js`, `wepppy/weppcloud/static/js/gl-dashboard/data/query-engine.js`, `wepppy/weppcloud/templates/reports/omni/omni_scenarios_summary.htm`, `wepppy/weppcloud/templates/reports/omni/omni_contrasts_summary.htm`, `tests/weppcloud/utils/test_helpers_paths.py`, `tests/weppcloud/routes/test_run_context.py`, `tests/weppcloud/test_omni_report_templates.py`, `wepppy/weppcloud/static/js/gl-dashboard/__tests__/scenario-manager.test.js`, `wepppy/weppcloud/static/js/gl-dashboard/__tests__/query-engine.test.js`

## Objective
Support nested composite runid slugs so GL Dashboard batch projects can target Omni scenarios/contrasts using existing `/runs/<runid>/<config>/...` and `/query-engine/runs/<runid>/<config>/...` route patterns.

Target nested slug forms:
- `batch;;<batch_name>;;<runid>;;omni;;<scenario_name>`
- `batch;;<batch_name>;;<runid>;;omni-contrast;;<contrast_id>`

## Problem Summary
- `gl-dashboard` builds composite runids for Omni access:
  - scenarios: `/runs/<parent_runid>;;omni;;<scenario>/<config>/...`
  - contrasts: `/runs/<parent_runid>;;omni-contrast;;<id>/<config>/...`
  - Source: `wepppy/weppcloud/static/js/gl-dashboard/scenario/manager.js`
- Query Engine calls pass scenarios in a JSON request-body `scenario` field, but route contrasts via composite runid in the URL.
  - Source: `wepppy/weppcloud/static/js/gl-dashboard/data/query-engine.js`
- Batch runids are already composite (`batch;;<batch_name>;;<runid>`). Batch + Omni therefore requires a nested slug if you want Omni behavior to survive route hops.
- `load_run_context()` ignores `?pup=` whenever the runid contains `;;`, so `?pup=omni/...` cannot be used to “enter” Omni from a batch runid.
  - Source: `wepppy/weppcloud/routes/_run_context.py`

### Historical Blockers (Resolved)
1. Backend WD resolution rejects nested composite runids.
   - `get_wd()` hard-requires exactly 3 segments for any runid containing `;;` and raises on `len(parts) != 3`.
   - Source: `wepppy/weppcloud/utils/helpers.py:get_wd`
2. Frontend deep-linking can double-nest.
   - `resolveParentRunId()` only strips `;;omni;;...` / `;;omni-contrast;;...` when `parts.length === 3`.
   - If `ctx.runid` is already nested (5 segments), URL rebuilds can produce `...;;omni;;X;;omni;;Y`.
   - Sources: `wepppy/weppcloud/static/js/gl-dashboard/scenario/manager.js`, `wepppy/weppcloud/static/js/gl-dashboard/data/query-engine.js`

## Scope
- Backend: update `get_wd()` to resolve nested batch+omni slugs (no recursion; no support for nested omni on non-batch composite parents).
- Frontend: update `resolveParentRunId()` so it strips Omni suffixes regardless of the total segment count.
- Access control: batch composite slugs (and nested batch+omni children) are Admin/Root-only because batch runs are not tracked in the `Run` ownership table.
- Tests: add regression coverage for the exact nested slug forms required by batch + Omni.

## Non-goals
- No generalized “arbitrary nesting” contract beyond the two supported batch+omni nested forms (5 segments).
- No changes to `load_run_context()` pup-query ignore behavior in this package (batch+omni is intended to work without `?pup=`).
- No changes to Query Engine API payload format or contrast routing semantics.

## Implementation Plan

### Phase 0: Clarify Doc Contract (Spec) (Done: `cdb700135`)
- `docs/composite-runid-slugs.md` should define composite runid slugs as `3+` `;;`-delimited segments (common forms are 3 and 5 segments).
- Update the doc to explicitly define “Omni suffix slugs” as: `<parent_runid>;;omni;;<scenario_name>` and `<parent_runid>;;omni-contrast;;<contrast_id>` where `<parent_runid>` may itself be composite (for example `batch;;...;;...`).

Deliverable:
- Doc tweak only (no behavior change).

### Phase 1: Backend `get_wd()` Nested Omni Suffix Support (Done: `38dabea20`)
Update `wepppy/weppcloud/utils/helpers.py:get_wd` to recognize nested batch+omni suffixes at the end of the runid and resolve the parent batch WD directly (no recursion):

Parsing rule:
- Let `parts = runid.split(';;')`.
- If `len(parts) == 5` and `parts[0] == "batch"` and `parts[3] in {"omni", "omni-contrast"}`:
  - `batch_name = parts[1]`
  - `parent_runid = parts[2]`
  - `leaf = parts[4]` (`scenario_name` or `contrast_id`)
  - `parent_wd = get_batch_run_wd(batch_name, parent_runid)`
  - `child_wd = os.path.join(parent_wd, "_pups", "omni", ("scenarios"|"contrasts"), leaf)`
  - Call `_ensure_omni_shared_inputs(parent_wd, child_wd)` (existing behavior).
  - Return `child_wd`.

Guard rails:
- Preserve existing 3-segment parsing for `batch`, `culvert`, `profile` when the runid does not end with an Omni suffix.
- For runids containing `;;` that do not match known patterns, keep explicit failure (do not silently fall back to primary WD guessing).
- Nested omni suffixes are not supported for non-batch composite parents.

### Phase 2: Frontend Parent Runid Resolution (Done: `4d2725f1f`)
Update both:
- `wepppy/weppcloud/static/js/gl-dashboard/scenario/manager.js:resolveParentRunId`
- `wepppy/weppcloud/static/js/gl-dashboard/data/query-engine.js:resolveParentRunId`

Desired behavior:
- If a runid ends with `;;omni;;<x>` or `;;omni-contrast;;<x>`, strip the trailing 2 segments and return the remaining `parent_runid` (even if the parent itself contains `;;`).

Implementation rule (JS):
- `const parts = raw.split(';;');`
- If `parts.length >= 3` and `['omni','omni-contrast'].includes(parts[parts.length - 2])`:
  - `return parts.slice(0, -2).join(';;');`

### Phase 3: Regression Tests (Done: `38dabea20`, `4d2725f1f`)
Backend (pytest, unit):
- Extend `tests/weppcloud/utils/test_helpers_paths.py`:
  - Add a test that stubs `_exists` and asserts:
    - `get_wd("batch;;spring-2025;;run-001;;omni;;treated", prefer_active=False)` resolves to `/wc1/batch/spring-2025/runs/run-001/_pups/omni/scenarios/treated`
    - `get_wd("batch;;spring-2025;;run-001;;omni-contrast;;3", prefer_active=False)` resolves to `/wc1/batch/spring-2025/runs/run-001/_pups/omni/contrasts/3`
  - Add “no regression” coverage for existing 3-segment slugs (`batch`, `culvert`, `profile`, `omni`, `omni-contrast`) plus malformed composite shapes.
  - Assert `_ensure_omni_shared_inputs()` is invoked for nested batch+omni resolution (no real filesystem symlink assertions).
  - Add `tests/weppcloud/test_omni_report_templates.py` to pin omni report link generation when `runid` is composite/nested.

Backend (pytest, routes):
- Add `tests/weppcloud/routes/test_run_context.py`:
  - Invalid composite runids abort with 404 (no 500s).
  - `load_run_context()` continues to ignore `?pup=` when `runid` contains `;;`.

Frontend (jest, unit):
- Extend `wepppy/weppcloud/static/js/gl-dashboard/__tests__/scenario-manager.test.js`:
  - Add a deep-link case where `ctx.runid` is already nested (`batch;;...;;omni;;undisturbed`) and ensure `buildScenarioUrl()` does not double-nest.
- Extend `wepppy/weppcloud/static/js/gl-dashboard/__tests__/query-engine.test.js`:
  - Add a case where `ctx.runid` is nested and contrast routing still produces a single Omni suffix (no repeated `;;omni-contrast;;`).
  - Add a scenario query case where `ctx.runid` is already omni-suffixed and confirm Query Engine routing strips to the parent runid before applying the body `scenario` parameter.

## Validation (Completed)
- `wctl run-pytest tests/weppcloud/utils/test_helpers_paths.py tests/weppcloud/routes/test_run_context.py tests/weppcloud/test_omni_report_templates.py --maxfail=1`
- `wctl run-npm test -- static/js/gl-dashboard/__tests__`

## Manual Validation Checklist
1. Confirm batch+omni WD resolution:
   - `get_wd("batch;;<batch>;;<runid>;;omni;;<scenario>")` resolves to `<batch_run_wd>/_pups/omni/scenarios/<scenario>`.
2. Open GL Dashboard on a nested batch+omni runid URL and verify:
   - scenario/contrast fetches hit the correct `/runs/...` route without 404.
   - Query Engine contrast requests hit `/query-engine/runs/<nested_runid>;;omni-contrast;;<id>/<config>/query` exactly once (no double nesting).
3. Deep-link reload test:
   - Refreshing the page on the nested URL does not break subsequent navigation or cause repeated suffix growth.

## Acceptance Criteria
- Backend `get_wd()` resolves nested `batch;;...;;omni...` and `batch;;...;;omni-contrast...` slugs without raising on segment count.
- GL Dashboard can deep-link into nested slugs and continue to build correct scenario/contrast URLs (no double nesting).
- Added unit tests cover the nested forms and pass under the standard gates.
- Existing 3-segment composite slug forms continue to resolve unchanged (batch/culvert/profile/omni).
- Omni report templates preserve composite parents when building scenario/contrast links.

## Follow-ups / Known Gaps
- None (omni report templates now preserve composite parents when building links).
