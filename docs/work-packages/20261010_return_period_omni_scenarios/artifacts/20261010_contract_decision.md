# Contract decision: return-period Omni comparisons

Prepared: 2026-10-10 17:26 UTC.
Starting implementation revision: `8b32a5c8c7d7eba52e947c8619b1dff2d8435e77`.
Classification: intended behavior enhancement, not a conformance repair.

## Authority and exact delta

Operator authorization is the initiating request: add `OMNI Scenarios Selection`
to Configuration, list completed project scenarios with unchecked checkboxes,
add a scenario column and scenario-specific dates/values, and download the
concatenated table. That authorizes the feature; no commit authority was given.

The new [domain contract](../../../ui-docs/contracts/return-period-omni-scenarios-contract.md)
records the normative delta. Applicable unchanged contracts are the shared
[controller contract](../../../ui-docs/controller-contract.md) (presentation,
request construction, and round trips) and
[output-scope contract](../../../schemas/output-scope-contract.md) (consistent
baseline/Roads selection). Base report shell context remains required per
`docs/dev-notes/weppcloud-base-report-shell.md`. No conflict is identified.

Rationale: row concatenation preserves independently ranked event dates and
matches the requested CSV. A shared-date join is incorrect. Default empty
selection preserves established output and avoids unnecessary child loading.

Compatibility plan: no-selection HTML/CSV and extraneous reports retain their
existing shapes; only explicitly selected simple reports gain `Scenario`.
Repeated `omni_scenario` parameters preserve exact names. Scope and report
filters propagate identically. No stored CSV/parquet/NoDb schema changes.
The choice of current-project label, explicit apply button, empty-state policy,
and extraneous-view retention are bounded implementation decisions documented
in the contract for review.

## Source boundary and security

Implementation is limited to `wepppy/weppcloud/routes/nodb_api/wepp_bp.py`,
`wepppy/weppcloud/templates/reports/wepp/return_periods.htm`, focused tests,
and affected report documentation. A small adjacent helper is permitted only
if it simplifies discovery without broadening scope. Read existing Omni state;
do not modify Omni orchestration or ranking algorithms.

High security triage: URL-selected filesystem children and CSV download change.
Use server-discovered names and direct resolved-path containment, preserve
parent authorization/CAP, escape HTML labels, and use the existing CSV writer.
No authentication, permissions, runtime identity, queue, or storage redesign.

## Regression and artifact evidence

The contract's state and query matrices are the acceptance checklist. Add
route and real-template regression tests, direct filesystem/symlink tests,
browser navigation/selection evidence, and parsed CSV readback with deliberately
different scenario event dates. Cover baseline/Roads without fallback, legacy
completed results, missing optional state, empty filtered reports, and restoration.
Existing outputs remain in normal archive paths; no new persisted artifact.

Readiness must not trust job state alone: `_post_omni_run` currently logs and
continues if return-period refresh fails. `_get_omni_scenarios` only checks
directory/NoDb presence and is insufficient to establish completion.

Review refinements: modern completion requires the existing loss artifact and
READONLY finalization, with explicit current-attempt evidence taking precedence;
legacy metadata absence is distinct from a present-empty state list. Readiness
requires scoped staged event/rank datasets and readable child state. Containment
anchors the scenario root in the authorized project and allows normal parent
shared-input links. Generated scenario prefixes keep new CSV labels safe.
Comparison evaluation bypasses existing JSON memoization (`meoization=False`)
because its validation omits method/interval choices; add warmed-cache regression.

## Reviews and ancestor

Two independent read-only contract reviews approved the amended contract.
Findings and post-fix confirmations are retained in
[review disposition](20261010_contract_reviews.md).
Checkpoint ancestor revision: pending explicit commit authority.
Implementation must not begin until that standalone ancestor commit exists.

Operator granted commit/implementation authority in the follow-up `yes. commit
and proceed`; initial checkpoint committed as `c5358daa7` before source edits.
Artifact-path clarification: `OmniArtifactExportService.scenarios_report` accepts
current `wepp/output/interchange/loss_pw0.out.parquet` and legacy
`wepp/output/loss_pw0.out.parquet`. The initial contract named only the latter;
clarify both before implementing current-layout discovery. This preserves the
approved completed-current-and-legacy scope rather than narrowing it to legacy.
