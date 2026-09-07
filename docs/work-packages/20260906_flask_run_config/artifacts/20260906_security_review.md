# Security Review

Reviewer: flask_security_review, 2026-09-06 UTC. Owner: root.
Scope: routes/_run_config.py, app registration and regression tests.
Checkpoint ancestor: 5f407550a. Impact: high (shared dispatch boundary).

## Findings and verdict

No blocking implementation findings; zero unresolved medium/high findings.
Checkpoint findings on early error disclosure and valid legacy forms are closed.
Uniform generic 404 does not expose saved metadata. Valid resolved requests run
normal guards; no generic authorization replacement or claim rewriting exists.

## Surface checks and evidence

Real-file tests cover valid metadata, missing/empty/malformed identity and unsafe
tokens. Existing path containment rejects escaping PUP paths. Read-only JSON
lookup avoids jsonpickle execution and NoDb initialization. Relative redirects
use the exact matched rule, safe token and original query. Mutations dispatch
once with unchanged bodies. CSRFProtect tests demonstrate missing-token rejection
and valid-token acceptance. Denied requests and login redirects are preserved.
Discarded response resources close and endpoint-issued cookies survive.

No new dependencies, outbound calls, secrets, persistence writes, locks, queue
edges or deployment mechanics. Existing downstream service policies are deferred.
Operators can revert app registration to roll back; no data repair is required.

## Release limitation

Code review passes. Production identity/mount and real browser deployment checks
remain release-time obligations; this package does not claim live rollout.
