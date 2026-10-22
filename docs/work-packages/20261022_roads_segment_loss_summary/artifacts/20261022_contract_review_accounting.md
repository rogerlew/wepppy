# Independent segment-summary accounting contract review

## Verdict and scope

**APPROVED for the standalone contract checkpoint.** No unresolved high or
medium accounting findings remain. This approves the specified behavior before
implementation, not a generated summary, release or deployment.

Reviewer: independent `accounting_contract_review` agent, 2026-10-22.
Starting WEPPpy revision: `61f17b0b7cb77befa8fa9441c638be756e4035d0`.
Runtime files, canonical specifications and the native repository were read only.
This review artifact is the reviewer's only edit in this package.

Reviewed the [canonical contract](../../../schemas/roads-segment-loss-summary-contract.md),
[ADR-0103](../../../adrs/ADR-0103-roads-segment-loss-source-attribution.md),
[decision record](20261022_contract_decision.md), package and active ExecPlan,
plus the affected output-scope/Roads specification sections. Inspected the current
summary producer and native PASS schema/parser and calendar implementation.

## Findings and disposition

| Finding | Severity | Final disposition |
| --- | --- | --- |
| Equal observed source calendars alone could admit a commonly truncated record and bias annualization | Medium | Resolved: positive persisted climate input_years defines N; sources must contain exactly N consecutive complete years, with the persisted start checked when available. Full-year julian coverage, global simulation-day continuity and PASS/WAT equality are required. |
| Profile scope and aliases lacked a deterministic rule for single-OFE non-inslope or unknown legacy designs | Medium | Resolved: remainder design takes precedence, then multiple OFEs, then proven inslope designs; remaining cases are explicitly unclassified_profile with NULL prism alias. |
| The revised calendar paragraph reused N for both years and annual days | Medium | Resolved before approval: julian runs from 1 through the individual year's record count; N remains simulation duration. |
| Required NULL metrics could be silently omitted by SQL SUM | Clarification | Explicit NULL/NaN/infinity rejection now precedes aggregation. |
| Provenance paths could be mistaken for raw PASS files instead of consumed Parquet | Clarification | Paths and hashes now identify the consumed Parquets, with segment_run_id as row identity and a separate manifest hash. |
| Filtering failed records might be misread as permission for partial Roads execution success | Clarification | Existing whole-run failure policy is explicitly preserved. |

## Numerical and source conclusions

The source change repairs the confirmed attribution defect: original segment
PASS records are selected by manifest native ID, while receiving-hillslope IDs
remain context. Native PASS declares runvol/sbrunv/gwbfv as volume, tdet/tdep as
mass and sedcon fields as mass per volume. The specified annual-volume,
detachment, deposition and concentration-times-runoff export formulas therefore
have the documented units. Native NO EVENT parsing retains gwbfv while setting
nonapplicable event fields to zero, so complete daily records are necessary even
when no surface export occurs.

N is the execution duration, including zero-export years. Calendar validation
must admit native CLI-supplied 365/366-day calendars; recomputing Gregorian leap
rules would unnecessarily narrow the existing native contract. Supported legacy
climates may lack calendar_start_year, but still require input_years and complete
contiguous source coverage. Missing duration is an explicit failure, not an
inferred event-year denominator.

Full stationary native OFE areas provide modeled area. Neither uploaded road
width times length nor receiving-hillslope area substitutes for MOFE footprint.
Original source responses are not multiplied by Roads aggregate-accounting
weights. The table describes every completed manifest profile, including
replacement remainder profiles; summing its rows is not a statement about
incremental road effect or routed watershed export.

Signed native detachment/deposition remain visible. Delivery ratio is defined
only for positive detachment and is not clipped. The prism alias is conservative:
only a proven single-OFE inslope profile receives detachment there; mixed,
remainder and unclassified profiles retain the general profile values and NULL
prism/buffer aliases. Existing columns remain present. Schema-level unit metadata
avoids renaming existing CSV headers through the shared converter.

## State and implementation acceptance matrix

These are required implementation checks, not claims that new runtime tests have
already passed.

| State/input | Required outcome |
| --- | --- |
| Manifest missing or not a list | Explicit preparation error; existing summary preserved. |
| Empty manifest or only skipped/failed records | Typed empty table without requiring PASS, WAT or a source calendar. Existing execution-failure policy remains. |
| Omitted legacy status/descriptive fields | Omitted status remains completed; optional descriptions may be absent; unknown design is labeled rather than fabricated. |
| Populated valid profiles | One row per unique positive native ID, with own-source values and complete execution coverage. |
| Several profiles share a target or uploaded segment | Distinct profile rows; target-loss changes cannot affect numerical values. |
| NO EVENT year or groundwater-only output | Include the year in N and retain native groundwater contributions. |
| Partial year or missing entire year across all selected sources | Fail expected-duration/calendar validation; do not annualize the shortened record. |
| Replacement MOFEs, remainder, mixed and unclassified profiles | Full native footprint, explicit scope precedence and contracted NULL aliases. |
| Duplicate IDs, missing sources, malformed geometry or NULL/nonfinite required values | Explicit error before publication, without zero substitution. |
| Native source or manifest changes during production | Pre/post hash validation rejects the generation. |
| Write/publication failure | Preserve the previous summary and its mode; retain any written visible pending candidate and identify it in the error/log. |
| Retry, authorized browser/CSV access and archive/restore | Successful publication uses the normal path; verify actual values, headers, bytes, modes and visibility through existing workflows. |

Also test arithmetic overflow after products/sums/division, not only finite input
cells. A finite row must not become a published infinite annual summary. Keep
baseline, original segment sources, canonical PASS and aggregate water products
byte-identical during isolated validation.

## Residual risks and checkpoint conditions

The source formula is suitable for this diagnostic; it does not resolve short
segment geometry, dominant-road geometry, sediment routing or road-only erosion
inside mixed profiles. The conservative aliases deliberately expose those limits.

Implementation still needs independent numerical oracles, actual writer/rollback
and alias tests, an isolated UM1 controller regeneration, Parquet/CSV comparisons,
and the specified browser/archive evidence. Existing wrong-join tests cannot be
used as correctness oracles. Security review owns publication containment and
mode/identity details. No new native release or scientific-model revision is
needed for the approved bounded reducer.

The approved contract amendments must be committed as an ancestor before runtime
implementation. Subsequent substantive contract changes require renewed review.

## Reviewed fingerprints

| Document | SHA-256 |
| --- | --- |
| roads-segment-loss-summary-contract.md | `9a5e46ea6445241f22fd2ca9686239e1c455db5afa6151852159cbc6e5b64b0d` |
| ADR-0103-roads-segment-loss-source-attribution.md | `bc07494d8b0867142de0b2532bcf24c2c49304bf26a41ee95d289e6869d04ed3` |
| 20261022_contract_decision.md | `780da5633833e84af4713fd2ec3ac6ddb5d585e1006d1613819fbb8b1d58dfc8` |
| repair_execplan.md | `eb5929cc44b30e1730225a70dd00072eeb5ef7055d5adbc512745d1ceb58cd0f` |
