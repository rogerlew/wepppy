# Flow-duration panel tracker

Updated: 2026-10-10 20:28 UTC. Phase: discovery/scaffold complete; decisions open.
Starting revision: `189d10649`. Security impact: high for future data-query
implementation; dedicated security review required. No review approval claimed.

## Completed

- Inspected graph registration, loader, palette, state and renderer seams.
- Verified baseline naming and named colors from active dashboard code.
- Inspected daily schemas and read actual baseline/Omni source counts.
- Recorded source distinction, proposed requirements, draft contract and active plan.

## Next

Verify source/outlet identity and rain-on-snow classification. Formalize the
accepted ranking/data-quality policy
in [research](notes/probability-and-data-quality.md), prepare the ADR and commit
reviewed ancestor before production edits. Daily resolution, warm-up and export
questions are answered. See [active plan](prompts/active/flow_duration_execplan.md).

## Decisions and risks

Confirmed by user: Flow duration panel; two source radios; linear/log x-axis;
Omni naming/color parity. Existing Undisturbed/Burned labels remain canonical.
Daily sampling, default two-year warm-up, return-period Year selection, no
seasonal filters, no CSV, and hover values/probability are accepted. Optional
rain-on-snow exclusion needs a verified definition. Scientific formulas and listed defaults are accepted; verification and review
remain. No implementation,
model output mutation, source regeneration, commit/push or deployment performed
for this scaffold. Main risks: wrong outlet field/ID, daily population truncation,
zero/missing-day bias, parent-data substitution, unequal periods, and graph
renderer assumptions about shared year coordinates.

## Validation

Scoped lint passed: 6 package documents, draft contract and PROJECT_TRACKER,
zero errors/warnings. Whitespace checks passed for these changes. No runtime tests
needed for documentation-only changes. Actual-source inspection is evidence of
availability only, not a flow-duration correctness claim.

Follow-up: verified dashboard has no Unitizer preference integration; fixed
metric labels/conversions are current behavior. D-04 now treats Unitizer/English
units as additional scope, not an existing mechanism to reuse.

Operator decision update (2026-10-10): each scenario uses its own available
eligible record, for performance; no common valid-date intersection. Show each
period and N. Other recommendations accepted: fixed m³/s, Weibull ranking,
retained ties/zeros, disclosed missing-day exclusions and invalid-record errors;
hillslope/linear-x/linear-y defaults; baseline plus available Omni with existing
visibility behavior; baseline output scope only; existing persistence conventions.
Rain-on-snow defaults unchecked and uses shared excluded dates when enabled;
classifier, mask construction and event-window definition remain to verify.
This optional mask does not impose a shared flow record. These decisions
supersede earlier proposals; source checks, ADR and independent review remain.
