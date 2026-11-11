# Correctness review — WebSocket run authorization

Date: 2026-11-11. Independent read-only reviewer: `implementation_correctness`.
Baseline: ratified ancestor `6a06ad49a`; implementation worktree before forest.

## Verdict

**CODE APPROVED. Environment acceptance pending.** Restore lookup now handles exact-child and parent bindings, canonical serialized configuration, and missing legacy child trees. Command-bar terminal failures are visible, middleware preserves the explicit 400 Authorization-header rejection, and standalone pages receive the shared transport helper.

The reviewer did not independently rerun the suites or observe forest acceptance.
This approval does not waive broad validation, deployed browser evidence, or
cleanup. Final execution receipts are retained separately.
