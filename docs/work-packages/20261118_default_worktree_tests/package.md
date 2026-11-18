# Default isolated testing and opt-in Disturbed matrix

Status: Complete locally; not integrated, 2026-11-18 UTC.

The operator requested that the isolated-worktree workflow become the default
and that the Disturbed matrix not run unnecessarily. Make `wctl run-pytest`
the canonical isolated/preflight command, retain `run-pytest-worktree` as an
alias, and name the previous shared-container command `run-pytest-shared`.
Keep the separately requested sharded workflow unchanged. Make only the native
Disturbed matrix and its dependent summaries opt-in with
`--run-disturbed-matrix`; keep lightweight Disturbed contracts and all other
matrix selection unchanged. Explicitly record this operator-authorized change
in test-selection policy; do not rewrite historical validation receipts.

Complexity budget: command registration changes, one small pytest selection
plugin and regression tests. No new dependencies, service changes, schema
mutation, scientific defaults or parameterization changes. Security impact: low;
existing isolated-runner boundaries remain unchanged. No ADR required.

[ExecPlan](prompts/completed/implementation_execplan.md), [tracker](tracker.md).

Validation: 113 passed and 99 matrix items deselected; explicit collection restores
all native cases, and Roads still collects 516. See [evidence](artifacts/validation.md).
