# Flask run config authority

## Purpose and context

Correct stale Flask config URLs using saved run metadata. The app in
wepppy/weppcloud/app.py registers URL preprocessors and blueprints; existing
routes/_run_context.py resolves active directories. Caddy bypass services are
excluded. This is a working implementation, not a scaffold.

## Progress

- [x] Operator approved scope; contract prepared.
- [ ] Independent checkpoint reviews and ancestor commit.
- [ ] Implement shared hook and regression tests.
- [ ] Validate and review final implementation.

## Plan of Work

First commit the reviewed contract decision. Add a small Flask hook module and
register it once on the application. Read safe JSON identity from the resolved
active root, normalize view arguments, and redirect successful reads after guards.
Add tests using actual files and Flask clients. Run focused tests through wctl,
then the required full suite. Record failures and review dispositions in tracker.

## Validation and Acceptance

From the repository root run wctl run-pytest on the new route hook tests and
tests/weppcloud/routes/test_run_context.py, then wctl run-pytest tests --maxfail=1.
Old GET URLs must redirect with suffix/query intact; POST bodies dispatch once;
denied requests must not expose canonical locations. Lint changed documents.

## Decision Log

2026-09-06 UTC: use response-stage successful-read redirects so individual guards
remain authoritative. Use raw JSON metadata to avoid controller initialization.

## Surprises & Discoveries

The existing context hook covers only an allowlist; app registration is necessary
for all matched Flask run routes.

## Outcomes & Retrospective

Pending implementation. No production deployment or data migration performed.

## Recovery and dependencies

No new dependencies or run writes. Revert the hook registration and module to
rollback application behavior. Durable rules live in the canonical schema doc.
