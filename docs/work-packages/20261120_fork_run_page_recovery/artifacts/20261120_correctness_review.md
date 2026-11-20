# Fork destination page correctness review

Reviewer: independent correctness reviewer. Accepted at 2026-11-20 20:58:57 UTC.
No medium or high finding remains in the reviewed scope.

The production URL preprocessor defers only the project view's context
resolution. Tests exercise the Flask request path, including that preprocessor
and the after-request query-cookie hook, with disposable Redis, actual RQ job
records, and temporary copies of the required file layout. The route tests
stub model context construction and account lookup. Actual Jinja tests cover
the run page's map controls and status markup. Query API tests exercise the
existing-credential denial and wrong-config rejection.

Tests render the actual project header and WEPP Reports templates and exercise
the separately authorized report response. GL Dashboard's existing catalog
tests cover holding SQL, resuming when ready, and retry. Existing successful
and completed legacy projects keep normal entry. Other domain dashboard links
and Omni descendant navigation remain outside the exact destination path.
No model output generation or queue mutation is part of the change.

Production-equivalent verification of a complete page with real scientific run
data is a separate rollout check. The local tests do not establish deployment.
