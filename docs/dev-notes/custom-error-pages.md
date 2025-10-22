# Custom Error Pages
> Observations and implementation notes for improving WEPPcloud error responses.

## Current Findings
- `exception_factory` (`wepppy/weppcloud/utils/helpers.py:211`) always serializes a JSON payload with a `Success: False` envelope and stack trace details, even when HTML pages call it (for example `wepppy/weppcloud/routes/weppcloud_site.py:22`). The helper writes the stack trace to `<runid>/exception_factory.log`, but it does not negotiate content type with the caller.
- The wrappers `handle_with_exception_factory` and `authorize_and_handle_with_exception_factory` (`helpers.py:291` and `helpers.py:316`) surround most blueprints. They re-raise deliberate `HTTPException`s but convert any other exception into the same JSON response, so HTML views fall back to machine-friendly JSON instead of rendering a page.
- Run lookups abort with plain Werkzeug error pages: `load_run_context` (`wepppy/weppcloud/routes/_run_context.py:35`) raises `abort(404, ...)` when the run directory is missing, and `runs0_nocfg` (`wepppy/weppcloud/routes/run_0/run_0_bp.py:84`) aborts with 404 when `Ron.getInstance` cannot load a configuration. These messages currently appear as the default Flask 404.
- Private runs trigger `abort(403)` inside `authorize` (`helpers.py:242`). Callers see the stock 403 response, which hints that the run exists and does not offer guidance about private projects.
- The browse microservice already ships a styled 404 template (`wepppy/weppcloud/routes/browse/templates/browse/not_found.htm`) with the desired layout.

## Potential Pain Points
- API callers that expect JSON (XHR/fetch) often send `Accept: */*`; naïvely preferring HTML for browsers could break them. We need a reliable way to detect when JSON is required (e.g., check `request.accept_mimetypes` preference score and whether `request.accept_mimetypes["application/json"] >= request.accept_mimetypes["text/html"]`).
- Some code paths call `exception_factory` outside the view wrappers (direct `return exception_factory(...)`). Any interface change must keep the existing signature and logging behavior stable.
- Switching private-run responses from 403 to 404 (to avoid confirming run existence) means auditing callers that rely on explicit 403 semantics.
- Introducing HTML templates means we need to ensure they are available in both the Flask app and any CLI contexts that might reuse helper functions.

## Feasibility Notes
- Flask exposes the negotiated content types via `request.accept_mimetypes`. Extending `exception_factory` to choose JSON vs HTML is straightforward and keeps the calling surface unchanged.
- We can render HTML errors by reusing the browse 404 layout as a base template and injecting dynamic copy for different scenarios (not found, unauthorized/private, unexpected error).
- Consistent messaging for run lookups can be centralized by adding custom error handlers (`app.errorhandler(404)`, `app.errorhandler(403)`, `app.errorhandler(500)`) in the Flask application factory. The handlers can call the updated helper so any `abort(...)` inherits the new styling automatically.
- Updating `runs0` / `runs0_nocfg` copy is low risk: both routes already funnel through `abort(404)` for missing runs. We only need to ensure the rendered message is ambiguous enough to preserve privacy.

## Implementation Plan
1. **Enhance error helpers**: Update `exception_factory` (and friends) to inspect accepted mimetypes, derive an appropriate status code, and choose JSON vs HTML rendering while preserving logging side effects and always surfacing stack traces (per transparency goal).
2. **Promote templates**: Move `wepppy/weppcloud/routes/browse/templates/browse/not_found.htm` into a shared `templates/errors/not_found.htm`, refactor it for extensibility (e.g., blocks for headline/body/action), and create any companion templates (`unexpected.htm`, etc.) using the same layout.
3. **Register Flask error handlers**: In `wepppy/weppcloud/app.py`, register handlers for 404/403/500 that delegate to the enhanced helper so every blueprint benefits without per-route changes.
4. **Adjust run routes**: Add explicit pre-flight checks in `runs0_nocfg` and `runs0` that collapse missing runs and unauthorized/private runs into a single 404 response with privacy-preserving copy (“This run is unavailable. It may be private or the link is incorrect.”). Update `authorize` or its callers to align with the new 404 behavior.
5. **Front-end audit**: Review `wepppy/weppcloud/controllers_js/*.js` to confirm which `Accept` headers our fetch wrappers send, and opportunistically replace jQuery usage with vanilla helpers when touching those files (long-term removal goal).
6. **Regression coverage**: Add tests that hit representative HTML and JSON endpoints, asserting that `Accept: text/html` returns the new templates and `Accept: application/json` (or `fetch` defaults) still receives JSON. Include a test for the run privacy message and for the always-on stack trace block.
7. **Docs & rollout**: Update README/dev notes if needed and communicate the change so front-end expectations stay aligned.

## Outstanding Questions
- What headers do our front-end fetch calls send today? We should confirm via a sweep of `controllers_js` usage (and matching browser captures) before finalizing the negotiation heuristic.
- Are there any lingering jQuery-only utilities in `controllers_js` that will complicate the vanilla JS migration once we touch a file? Track candidates for staged removal.
