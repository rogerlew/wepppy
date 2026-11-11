# Security review — WebSocket run authorization

Date: 2026-11-11. Independent read-only reviewer: `implementation_security`.
Baseline: ratified ancestor `6a06ad49a`; implementation worktree before forest.

## Verdict

**CODE AND FOREST ACCEPTANCE APPROVED.** No open high/medium code findings. Reviewed bounded restore ZIP identity without object deserialization, exact job/parent authority, strict JWT parsing, operation restrictions, browser credential handling, static service errors, and Caddy header filtering.

Final read-only evidence review approved the full regression result and
`20261111_forest_acceptance.json`: all 27 browser checks passed; the original
cleanup failure is preserved and scoped recovery removed both exact fixtures.
Health and runtime image identities are recorded. The reviewer did not rerun
tests or independently operate the browser. Production deployment is not claimed.

## Threat model and resolved finding

Assets: private project telemetry, sessions, signing keys and Redis channels.
Attackers: anonymous/unrelated callers, cross-run replay, hostile Origins and
accidental credential logging. Required ordering: identity, scope, run/config,
time and live revocation checks before upgrade or run-specific Redis access.
CWE-862/CWE-639 apply to the original missing authorization; CWE-922 applies to
credential retention.

S-01 (Medium): Caddy's default reverse-proxy error log could retain the incoming
subprotocol credential on upstream failure. The independent reviewer reproduced
this using a synthetic bearer value in a disposable network-isolated Caddy
instance. Both canonical Caddy configurations now delete
`request>headers>Sec-Websocket-Protocol` through the default log filter. The
reviewer verified the failure-path output was filtered and both configs adapt.
Closed on forest: the runtime Caddy filter and browser/log non-retention checks passed.

No production rollout is authorized. A rollback to the old validators restores
availability but reopens the original exposure and cannot close SEC-04.
