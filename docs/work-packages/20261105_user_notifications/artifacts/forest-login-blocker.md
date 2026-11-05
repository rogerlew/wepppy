# Forest baseline login blocker

Before notification activation, a real browser challenge/redeem succeeds but
password login returns the existing CAPTCHA validation error. The web container
cannot reach `https://forest.tail305ec9.ts.net:443` (connection refused), which is
its configured verification path. Host/browser access is healthy. Direct internal
`http://cap:3000/cap/<site-key>/siteverify` returns HTTP 200 and rejects an invalid
token using the existing secret. No verification bypass or credential change is needed.

The existing `utils/cap_verify.py` already supports `CAP_VERIFY_BASE_URL`, but dev
Compose does not forward it. Concrete proposed repair: add optional
`CAP_VERIFY_BASE_URL: ${CAP_VERIFY_BASE_URL:-}` to the web service environment,
and set only that host variable to `http://cap:3000/cap`. Keep the browser-facing
CAP URL unchanged. Activate with the already planned canonical targeted-web
deployment; no additional service recreation. Preserve this repair during the
notification-only rollback. Rollback of the repair itself removes that host key
and Compose line and uses the same targeted-web deployment.

This is a pre-existing login transport defect, independent of notification code.
Operator approval is pending because root AGENTS requires explicit approval for
unrequested authentication/runtime behavior changes. The patch is prepared at
`/var/tmp/notification-rollout-20261105/cap-verification-repair.patch`; no repair
configuration has been applied.

Independent review confirmed rq-engine has the same unreachable public route in
project/fork CAPTCHA verification. Include its environment mapping
`CAP_BASE_URL: ${CAP_VERIFY_BASE_URL:-${CAP_BASE_URL:-}}`; it has no browser asset
consumer. Interpolation was verified for absent, empty, relative and explicit
internal overrides. Both services are already in the targeted-web activation set.
Validate each helper with fresh and replayed tokens and invalid tokens, without
creating projects/jobs, then prove actual browser login. Approval remains pending.
