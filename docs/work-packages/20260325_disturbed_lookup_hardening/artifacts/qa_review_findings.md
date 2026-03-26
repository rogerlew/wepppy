# QA Review Findings

**QA Subagent**: `qa_reviewer` (`019d26e7-a26a-7f60-8fe8-266a2349d33c`)  
**Review Date**: 2026-03-25

## Findings and Disposition

1. **High**: Legacy schema-upgrade path could render `disturbed_class`-style rows unreadable (blank `luse/stext` with populated legacy key columns).
- Status: **Resolved**
- Fix:
  - Canonicalized `luse/stext` during upgrade when key values are discoverable from legacy columns in [`wepppy/nodb/mods/disturbed/disturbed.py`](/workdir/wepppy/wepppy/nodb/mods/disturbed/disturbed.py).
  - Hardened lookup reads to prefer non-empty values across both (`luse`,`disturbed_class`) and (`stext`,`texid`) pairs.
  - Added regression coverage: `test_upgrade_legacy_disturbed_class_rows_remain_readable`.

## QA Gap Follow-up

Requested QA testing gaps were addressed as follows:

1. Legacy upgrade readability regression test.
- Added in [`tests/nodb/mods/test_disturbed_lookup_persistence.py`](/workdir/wepppy/tests/nodb/mods/test_disturbed_lookup_persistence.py).

2. Route-level validation with real writer path (not fully stubbed).
- Added in [`tests/weppcloud/routes/test_disturbed_bp.py`](/workdir/wepppy/tests/weppcloud/routes/test_disturbed_bp.py):
  - `test_task_modify_disturbed_rejects_partial_table_payload`
  - `test_task_modify_disturbed_rejects_blank_rows_from_table_payload`

3. Blank/trailing row behavior from spreadsheet payloads.
- Added explicit rejection test for blank rows (`non-empty luse/stext` contract) in route tests.

4. Save -> extended lookup export non-clobber behavior.
- Covered in nodb regression `test_build_extended_lookup_writes_separate_extended_csv`.

## Residual Risks

- Full proxy-integrated end-to-end coverage (Caddy + browse service) is still out-of-scope for this unit/integration slice.
- Explicit row deletion via partial payload is blocked by design to avoid accidental data loss.

## Validation Evidence

- `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/test_disturbed_lookup_persistence.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods -k disturbed --maxfail=1`

---

## Reopen Cycle: UI Safeguards (2026-03-26)

**QA Subagent**: `qa_reviewer` (`019d27ab-6243-71e0-8634-fcd2a3d28ee1`)  
**Review Date**: 2026-03-26

### Findings and Disposition

1. **High**: reload failure while stale could hide recovery actions and strand users in locked state.
- Status: **Resolved**
- Fix:
  - Updated reload path to preserve stale lock state/recovery controls across failed reload attempts in [`wepppy/weppcloud/templates/controls/edit_csv.htm`](/workdir/wepppy/wepppy/weppcloud/templates/controls/edit_csv.htm).
  - Kept `Load Current Table` and `Refresh Page` controls visible when recovery attempts fail.

2. **Medium**: save error handling conflated all `409` responses into stale-table messaging.
- Status: **Resolved**
- Fix:
  - Added structured error parsing in editor save path and code-specific handling for:
    - `STALE_LOOKUP`
    - `LOOKUP_VERSION_UNAVAILABLE`
    - `PRECONDITION_REQUIRED`
  - Implemented in [`wepppy/weppcloud/templates/controls/edit_csv.htm`](/workdir/wepppy/wepppy/weppcloud/templates/controls/edit_csv.htm).

3. **Medium**: polling fetches could be cached by browser/proxy layers and under-detect staleness.
- Status: **Resolved**
- Fix:
  - Added `cache: "no-store"` for editor `lookup_meta` and `lookup_snapshot` fetches.
  - Added no-store headers on both lookup endpoints in [`wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`](/workdir/wepppy/wepppy/weppcloud/routes/nodb_api/disturbed_bp.py).

4. **Medium**: table lock implementation toggled `contenteditable` attributes broadly and could re-enable intentionally non-editable nodes.
- Status: **Resolved**
- Fix:
  - Removed blanket `contenteditable` rewrites; locking now uses non-invasive pointer/opacity/aria gating.
  - Implemented in [`wepppy/weppcloud/templates/controls/edit_csv.htm`](/workdir/wepppy/wepppy/weppcloud/templates/controls/edit_csv.htm).

5. **Medium**: reload/save/poll hardening lacked explicit regression assertions for no-store and recovery hooks.
- Status: **Resolved**
- Fix:
  - Added route/template assertions for:
    - no-store cache headers on lookup endpoints
    - no-store fetch directives in template script
    - stale-recovery option wiring (`recoveryAttempt: true`)
    - code-path constants for optimistic-concurrency UI handling
  - Coverage in [`tests/weppcloud/routes/test_disturbed_bp.py`](/workdir/wepppy/tests/weppcloud/routes/test_disturbed_bp.py).

### Reopen Residual QA Gaps

- No Playwright-style browser automation currently exercises polling cadence, stale banner transitions, and click-race behavior in a real DOM/network loop.
- Coverage is strong at route/contract level; UI interaction assertions remain template/logic-level rather than browser-driven.

### Reopen Validation Evidence

- `wctl run-pytest tests/weppcloud/routes/test_disturbed_bp.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods/test_disturbed_lookup_persistence.py --maxfail=1`
- `wctl run-pytest tests/nodb/mods -k disturbed --maxfail=1`
- `wctl run-stubtest wepppy.weppcloud.routes.nodb_api.disturbed_bp`
- `wctl check-test-stubs`
- `wctl run-pytest tests --maxfail=1`
