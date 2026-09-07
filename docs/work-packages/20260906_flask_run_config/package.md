# Flask run config authority

Implement the operator-approved Flask-only correction for stale config URLs.
Canonical behavior: `docs/schemas/flask-run-config-contract.md`. Security impact:
high because dispatch arguments cross authorization boundaries; dedicated review
required. No model, data-schema, queue or other service changes. Acceptance:
canonical Flask dispatch, guarded read redirects and intact mutation bodies.

2026-09-06 UTC: implementation and independent reviews complete locally.
36 focused tests passed; broad gate has an unrelated reproduced Roads test
failure. No production deployment. See tracker.md for exact validation limits.
