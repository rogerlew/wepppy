# Automatic deletion help

Status: active. Scope: understandable project deletion controls, state and help.

User approved the assessment on 2026-11-04, with exact labels “Disable automatic
deletion”, “Automatic deletion is enabled for [readable date]”, and “Automatic
deletion is disabled”; requested scoped tests, commit and push.

Security impact: low. Existing authentication, project scope, CSRF and TTL
persistence remain unchanged. Additive catalog status uses already-authorized
rows and existing freshness rules. No new infrastructure, dependencies, schema
migration, privileges, retention defaults or deletion behavior.

Compatibility plan: retain doc IDs/URLs, selectors, mutation payload and
`ttl_deletion_at`; add nullable `ttl_disabled` to catalog JSON only. Derive it
from current policy; never infer disabled from a missing date. Test legacy and
PostgreSQL readers, active/disabled/excluded/unknown/stale states, rendered
controls and table, saved state and failed mutation, help navigation/search.

Exit: scoped tests pass, independent review findings closed, controller bundle
rebuilt, docs validated, commits pushed. Production deployment is not included.
