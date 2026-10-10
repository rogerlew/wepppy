# Return-period simple report Omni comparisons

Status: Closed 2026-10-10 (code/local validation; not deployed).
Started: 2026-10-10. Owner: Codex; operator: requesting user.

Add a Configuration collapsible with unchecked completed Omni scenarios and
compare selected scenarios with the current project in simple return-period
tables and concatenated per-table CSV downloads.

The durable behavior and rationale live in the
[contract](../../ui-docs/contracts/return-period-omni-scenarios-contract.md).
Completed [plan](prompts/completed/return_period_omni_execplan.md).
Implementation `d252ff056`; artifact-discovery/Outlet correction `99981ce36`.

Security impact: high under the repository classification because this changes
a public report/download handler and scenario filesystem selection. Preserve
existing access control and require a dedicated security review before closure.
No stored data/schema migration, model parameterization, RQ, or deployment work.

Acceptance: selected scenarios retain their own event dates and values in
rendered tables and downloaded CSV; no-selection behavior stays compatible.
Complete independent correctness/security review, focused regression tests,
frontend checks, full Python sanity, and direct CSV/filesystem evidence.

See [tracker](tracker.md) and [checkpoint](artifacts/20261010_contract_decision.md).
Local evidence and gate limitations: [validation](artifacts/20261010_validation.md).
Independent correctness/security reviews approved. Not deployed.

Full Python sanity: 10,554 passed, 126 skipped. Frontend: 933 passed.
Existing unrelated lint failure and exception-tool drift are documented.
