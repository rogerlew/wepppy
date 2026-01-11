# Agent Prompt: Phase 2 Archive Console Pipeline

## Goal
Implement Phase 2 from `docs/work-packages/20260111_error_schema_standardization/tracker.md` by moving `archive_console.js` into the standard static-src build pipeline and updating references so assets are generated consistently.

## Scope
- Move source to `wepppy/weppcloud/static-src/` (choose the appropriate folder under static-src for JS sources).
- Update build tooling so `archive_console.js` is emitted into `wepppy/weppcloud/static/js/` during `wctl build-static-assets`.
- Update any template or import references to point to the built output path as needed.
- Ensure tests that import `archive_console.js` still work.

## Required changes
1. **Source relocation**
   - Identify the build pipeline in `wepppy/weppcloud/static-src` (scripts, package.json, build config) and place the source there.
   - Remove or deprecate the manually maintained file in `wepppy/weppcloud/static/js/` (do not leave two divergent sources).

2. **Build updates**
   - Update `wepppy/weppcloud/static-src` build config to include the new entry.
   - Verify output lands in `wepppy/weppcloud/static/js/archive_console.js`.

3. **References**
   - Find templates or code that reference `/static/js/archive_console.js` and ensure paths remain valid.
   - Update tests (especially `controllers_js/__tests__/console_smoke.test.js`) if import paths or stubs need adjustment.

4. **Documentation + tracker**
   - Update `docs/work-packages/20260111_error_schema_standardization/tracker.md` with Phase 2 progress and any open questions.

## Constraints
- Do not change the archive console runtime behavior or response handling beyond what is needed to move the asset.
- Keep ASCII only.

## Testing gates
- `wctl build-static-assets`
- `wctl run-npm lint`
- `wctl run-npm test -- console_smoke` (or closest equivalent if suite name differs)

## Notes
- Use `rg -n "archive_console" wepppy/weppcloud` to locate references.
- Prefer adding a clear comment in the build config describing the new entry point.
