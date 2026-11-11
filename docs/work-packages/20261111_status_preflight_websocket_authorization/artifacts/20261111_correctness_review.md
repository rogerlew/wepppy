# Correctness review — WebSocket run authorization

Date: 2026-11-11. Independent read-only reviewer: `implementation_correctness`.
Baseline: ratified ancestor `6a06ad49a`; implementation worktree before forest.

## Verdict

**CODE AND FOREST ACCEPTANCE APPROVED.** Restore lookup now handles exact-child and parent bindings, canonical serialized configuration, and missing legacy child trees. Command-bar terminal failures are visible, middleware preserves the explicit 400 Authorization-header rejection, and standalone pages receive the shared transport helper.

Final read-only evidence review approved the full regression result and
`20261111_forest_acceptance.json`: all 27 browser checks passed; the original
cleanup failure is preserved and scoped recovery removed both exact fixtures.
Health and runtime image identities are recorded. The reviewer did not rerun
tests or independently operate the browser. Production deployment is not claimed.
