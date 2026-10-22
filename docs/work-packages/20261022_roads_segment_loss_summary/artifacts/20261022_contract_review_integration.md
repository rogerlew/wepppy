# Independent contract review: integration and publication

Date: 2026-10-22. Reviewer: integration_contract_review. Implementation baseline:
WEPPpy `61f17b0b7`; native `c941cb6`. This review precedes runtime implementation.

## Disposition

Approve the proposed contract checkpoint. No unresolved high or medium finding
in the reviewed scope. This approves implementation against the contract, not
runtime correctness, security acceptance, or deployment.

Reviewed the canonical segment-summary contract, ADR-0103, package decision and
active ExecPlan; compared them with the existing Roads producer, native PASS
calendar conversion, manifest writers, report links and CSV download code.
The revised contract explicitly requires persisted execution duration, complete
source dates, WAT/PASS agreement, nullable unsupported aliases, manifest/source
hashes and typed empty output. Final reread confirms the requested Julian-bound
clarification and schema-level annual-unit metadata. Approval binds canonical
contract SHA-256 `9a5e46ea6445241f22fd2ca9686239e1c455db5afa6151852159cbc6e5b64b0d`,
ADR SHA-256 `bc07494d8b0867142de0b2532bcf24c2c49304bf26a41ee95d289e6869d04ed3`,
decision SHA-256 `780da5633833e84af4713fd2ec3ac6ddb5d585e1006d1613819fbb8b1d58dfc8`,
and active-plan SHA-256 `eb5929cc44b30e1730225a70dd00072eeb5ef7055d5adbc512745d1ceb58cd0f`.

## Scope and authority

The requested correction is source attribution in the existing diagnostic.
The old target-first join in `wepppy/nodb/mods/roads/roads.py:3895` can assign one
receiving-hillslope vector to several segment rows. Selecting the original
profile by `segment_run_id` removes that ambiguity without changing routing,
modeled geometry, physical water accounting or the native extension.

The amended Roads specification and output-scope contract identify the new
authority. ADR-0103 records the intentional numeric and alias changes. Keeping
all column names and labeling mixed/remainder profiles is a reasonable bounded
compatibility treatment; old numbers cannot be preserved while fixing their
meaning. No model rerun, production deployment or original UM1 mutation follows
from this approval.

## Valid states and noninterference

- Populated: one source-profile row per completed ID; target IDs supply context
  only. Multiple source profiles belonging to the same uploaded segment remain
  distinct. Selected source IDs must not collide with target IDs.
- Empty: an existing empty manifest, or only explicitly skipped/failed records,
  produces the complete typed schema without requiring PASS/WAT or a calendar.
  This does not relax the separate whole-run failed-segment policy.
- Legacy: omitted status means completed; absent descriptive fields remain
  supported. Unproven road-only attribution becomes `unclassified_profile` with
  a NULL prism alias. Existing historical artifacts are not certified on read.
- Invalid: missing manifest or completed sources, malformed/duplicate IDs,
  unknown statuses, NULL/nonfinite required metrics, unstable areas and
  incomplete/mismatched dates fail. Native finite signed detachment/deposition
  remain observable. No zero-filled missing source is admitted.
- Single storm: existing no-summary behavior is preserved.

Native PASS conversion emits EVENT, SUBEVENT and NO EVENT dates using its CLI
calendar (`wepppyo3/wepp_interchange/src/hill_pass.rs:364`). The contract correctly
avoids independently imposing Gregorian leap rules. Native stationary OFE area
validation can supply geometry; DuckDB can reduce existing source Parquets.

## Publication and downstream obligations

The manifest, H.pass and H.wat are consumed inputs and must be included in the
pre/post-read identity checks. Validate required metrics before SUM because SQL
aggregates can silently omit NULL values. Validate destination identity before
creating a temporary output. Same-directory atomic replacement, preserved mode
and umask-derived first creation must be tested with real files; failure retains
the old complete summary and propagates to resource regeneration.
The final contract retains visible uniquely named pending candidates on failure
and reports their paths. Verify successful retry while a prior failed candidate
remains; catalog discovery must not mistake that candidate for the canonical
summary or prevent regeneration from completing.

Keep provenance and annual-unit mappings in schema metadata. The existing CSV
exporter calls `project_table_for_output(include_units=True)` in
`wepppy/microservices/browse/_download.py:638`; adding field-level unit metadata
can change exported headers. Test exact existing CSV names as well as values,
NULL aliases and the header-only empty case. This is an implementation caution,
not a request to alter the download endpoint.

The existing report links are assembled in
`wepppy/weppcloud/routes/nodb_api/roads_bp.py:198`. Update their source description
and affected documentation if it continues to describe receiving-hillslope loss.
Retain existing authorization and visible paths. Canonical archive/restore must
preserve the summary bytes, modes and ordinary producer inputs, including the
persisted climate duration used for completeness validation.

## Smallest sufficient implementation validation

1. Exercise the real producer against small source Parquets: two roads sharing
   one target with different exports; a target-only distraction; a no-export
   year; MOFE and remainder areas; legacy unclassified scope; typed empty states.
2. Exercise actual validation/publication boundaries: required NULL/NaN/Infinity,
   duplicate/missing IDs, missing whole simulation year, date/OFE gaps, source
   and manifest drift, destination aliases, first-create umask, preserved mode,
   replacement failure and a successful retry. Verify old output bytes survive.
3. Run the unchanged controller regeneration flow in the isolated UM1 copy.
   Independently compare each of its 34 rows with original PASS annual sums and
   WAT areas. Record original/model/aggregate hashes before and after. Expected
   total and dominant-source values are acceptance anchors, not substitutes for
   checking every source row.
4. Exercise the actual browser/download CSV path and canonical archive/restore
   using local runtime identities. Verify populated and empty artifacts, source
   lineage, bytes/modes and preserved access behavior. Complete package test
   gates and independent correctness/security reviews before closure.

## Residual limits

No new producer exists at this checkpoint, so no runtime or browser behavior is
certified here. Pre/post hashes and atomic publication operate within the
existing single-writer Roads lifecycle; this review does not establish arbitrary
concurrent filesystem-adversary guarantees. The summary remains profile export,
not incremental road impact, road-only detachment for mixed MOFEs, buffer-only
export, or watershed outlet delivery.
