# MOFE ET and Deep-Percolation Area Weighting

**Status**: Open; scaffolded, implementation not started  
**Started**: 2026-10-20 18:45 UTC  
**Owner**: WEPPpy/wepppyo3 maintainers; requesting operator  
**Execution**: [ExecPlan](prompts/active/mofe_et_dp_area_weighting_execplan.md)  
**Tracking**: [Tracker](tracker.md)

## Overview

For hillslopes with multiple overland flow elements (MOFEs), raw `H*.wat`
ET components and deep percolation are local depths for each OFE. Three current
consumers incorrectly turn them into hillslope values: the native water-balance
report sums depths, dashboard event ET sums depths, and Features Export selects
only the terminal OFE. Correct the consumers to use each OFE's own area.

The operator requested a scaffold for those three fixes and immediate removal
of the disabled raw-water-balance section in `new_report.Rmd`. This package
does not claim implementation, deployment, or repair of existing projects.

## Scope

Included implementation milestones:

1. Correct ET and Dp spatial aggregation in
   `/workdir/wepppyo3/wepp_interchange/src/hillslope_watbal.rs`, its WEPPpy report
   facade, and cache compatibility.
2. Correct both event ET queries in
   `wepppy/weppcloud/static/js/gl-dashboard/data/wepp-data.js`, including the
   comparison baseline.
3. Correct the field-specific reduction of ET components and Dp in
   `wepppy/nodb/mods/features_export/temporal_wide_materializer.py` and its
   catalog/materialization integration, covering event, yearly, and
   annual-average exports.
4. Complete contract/ADR documentation, independent reviews, regression tests,
   fresh artifact readback, and a bounded cache regeneration/release handoff.

Completed scaffold cleanup: delete the commented raw-water-balance calculation,
its disabled map chunk, and obsolete section comments from
`weppcloudR/templates/scripts/users/chinmay/new_report.Rmd`.

Out of scope: WEPP process physics; raw WAT schema changes; replacing correctly
weighted `totalwatsed3` or `load_hill_wat_dataframe`; unrelated runoff/lateral-flow
or precipitation semantics; annualization policy changes; deletion of the shared
R `calc_watbal` helper or older `report.Rmd`; new infrastructure; production
deployment or bulk project mutation in this scaffold.

## Intended Behavior and Rationale

For hillslope h and day d, use local area `A_i = slplen_i * fwidth_i` in m²:

    ET_h,d = sum(A_i * (Ep_i + Es_i + Er_i)) / sum(A_i)
    Dp_h,d = sum(A_i * Dp_i) / sum(A_i)

All four source depths are mm. Weight each ET component by the same rule.
Annual values sum daily hillslope depths; annual averaging retains the
consumer's existing documented time selection/divisor unless separately
authorized. Subsequent watershed aggregation weights corrected hillslope
depths by hillslope area. Do not use cumulative upstream contributing area,
the terminal OFE, an unweighted mean, or a sum of OFE depths.

Spatial aggregation must precede temporal reduction. Sum areas once per day,
not over every day of a year. Preserve single-OFE equivalence and output
names/units. Treat runoff and lateral flow separately: their routing semantics
are not authorization to apply the ET/Dp reducer to every numeric column.

This active package records the operator's requested outcome and rationale;
before implementation, promote the durable rule to a current canonical
contract and complete the contract-first checkpoint. Source/tests are evidence
of the defect, not normative authority.

## Compatibility and Regression Plan

Keep existing entrypoint signatures, raw interchange columns, report labels,
scope selection, and export formats. Numerical report/export values change for
MOFE ET/Dp by design. Version affected report/export cache semantics so old
unweighted or terminal-OFE results are not silently served as corrected results.
Explicitly disposition supported historical caches whose source is absent;
do not invent replacement OFE areas or blanket-delete run artifacts.

Require unequal-area/unequal-flux fixtures, single-OFE controls, multiple days
and hillslopes, comparison queries, supported legacy layouts, empty/missing
inputs, invalid areas, duplicate rows, and cold/warm/stale caches. Define
exception policies at the contract checkpoint rather than silently treating
missing data as zero or falling back to unweighted values.

## Acceptance and Generated Artifact Gate

With OFEs of 250 and 750 m², ET values 2 and 6 mm, and Dp values 4 and 8 mm,
every corrected daily hillslope consumer must yield ET 5 and Dp 7 mm.
Two identical days yield ET 10 and Dp 14 mm before annual averaging.
Fresh native report Parquet, browser query responses, HTML/CSV, and selected
Features Export artifacts must agree with an independent volume/area oracle.
Existing TotalWatSed and daily-loader results must remain unchanged.

Retain the exact source artifact, revisions/native module hash, request and
scope, generated cache/export paths, semantic readbacks, and user-facing result.
An actual MOFE project in the development stack is required because existing
tests encode or omit the defective spatial behavior. Capture old and new
outputs without overwriting the evidence. Deployment and existing-project
repair are separate claims and require separate evidence.

Highest current claim: **diagnosed**, with package scaffold and inactive R
cleanup complete; aggregation remediation remains pending.

## Complexity Budget

Reuse the existing native report producer, SQL query engine, Features Export
materializer, and cache/version mechanisms. Permit no new dependency, queue,
service, datastore, daemon, privilege, protocol, or deployment topology.
Start with bounded, field-specific reducers. Any escalation needs retained
evidence that the simple approach missed actual acceptance, plus its smallest
alternative and operational/recovery cost.

## Review and ADR Gates

- **Security impact**: `none` for the scoped numerical expressions and removal
  of disabled R code; no auth, path, queue, subprocess, or permission changes.
- **Dedicated security review**: not required at scaffold scope. Re-triage if
  implementation changes a public handler, input/file boundary, or release wiring.
- **Correctness review**: independent artifact required before implementation
  closeout, using `docs/prompt_templates/correctness_review_template.md`.
- **Contract gate**: current contract amendments, two independent read-only
  reviews, and the required standalone ancestor checkpoint before UI-coupled
  implementation, per the contract-first standard.
- **ADR**: required before merge for changed aggregation/scaling formulas;
  draft it at the contract milestone. Record this conversation as the decision
  venue, operator as decision owner, and actual implementer/reviewers without
  inventing participants or approvals.

## Remediation Signals

Healthy: equal daily ET/Dp across the independent oracle, TotalWatSed reference,
report, dashboard, and export; unchanged single-OFE controls and routed fields.
Danger: multiplying by OFE count, terminal-OFE retention for local fluxes, stale
cache reuse, changed time divisors, or broad reducer changes to Q/latqcc.
Observe cold generation, warm reuse, and stale-cache regeneration on the same
candidate/project before handoff. No temporary mitigation is introduced.

## References and Deliverables

- [Audit baseline and consumer map](notes/consumer-audit.md).
- [Contract-first standard](../../standards/contract-first-change-standard.md).
- [Generated-artifact validation](../../standards/generated-artifact-validation-standard.md).
- [Parameterization ADR standard](../../standards/parameterization-adr-standard.md).
- [Features Export specification](../../../wepppy/nodb/mods/features_export/specification.md).
- [Interchange documentation](../../../wepppy/wepp/interchange/README.md).

Deliverables are the three bounded fixes, corrected regression expectations,
current contracts/ADR and user/operator/developer documentation, reviewed
artifact evidence, cache recovery instructions, and coordinated native release
provenance. The present delivery is only the scaffold and disabled R removal.
