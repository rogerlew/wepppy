# Soil Controller Migration Plan
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](../../../../dev-notes/controllers_js_jquery_retro.md).

> Checklist and status tracker for the `soil.js` helper migration.

## Controller Notes
- ✅ Replaced jQuery usage in `wepppy/weppcloud/controllers_js/soil.js` with `WCDom`, `WCForms`, and `WCHttp`.
- ✅ Wrapped legacy `controlBase` adapters so status, stacktrace, and RQ job UI remain functional without jQuery.
- ✅ Added helper-driven handlers for ksflag, disturbed `sol_ver`, and mode toggles; WS client lifecycle mirrors Landuse.

## Backend Alignment
- ✅ `wepppy/weppcloud/routes/nodb_api/soils_bp.py` now uses `parse_request_payload`, coercing integers/booleans/floats and preserving error semantics.
- ✅ Disturbed `sol_ver` endpoint accepts numeric payloads; ksflag updates consume native booleans.

## Testing
- ✅ Jest coverage via `controllers_js/__tests__/soil.test.js` (mode changes, ksflag, disturbed payloads, build submission).
- ✅ Added Flask unit tests in `tests/weppcloud/routes/test_soils_bp.py` covering mode updates, ksflag, and sol_ver routes.

## Follow-ups
- Monitor downstream consumers that expect string `sol_ver` values; all current call sites tolerate floats but flag regressions if they appear.
- Future controller migrations should reuse the Soil pattern when converting RRED or other soil-adjacent controls.
