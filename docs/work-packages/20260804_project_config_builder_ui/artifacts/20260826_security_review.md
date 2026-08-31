# WP07 security review

**Impact**: high.
**Disposition**: approved; no unresolved findings.

- The Flask page requires an authenticated session.
- API calls reuse the existing short-lived rq-engine JWT bridge and require the
  existing `rq:enqueue` scope; no credential is embedded in markup.
- The browser cannot submit a config token, filename, path, capability claim,
  or raw configuration key. The server remains authoritative for revision,
  constraints, roles, resolution, and creation.
- Advanced cell-size choices are rendered only when the authenticated API says
  the actor may override, and rq-engine independently enforces the role.
- Creation uses a cryptographically random idempotency key and suppresses an
  additional request while one is active.
- Response text is assigned through DOM text APIs; server values are not
  inserted as HTML.
- The WP06 writer remains strict and default-off; WP07 changes no deployment
  default or authorization boundary.

The broad-exception changed-file gate passed with a net delta of zero.
