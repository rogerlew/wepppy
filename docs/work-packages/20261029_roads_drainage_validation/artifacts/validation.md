# Validation and primary-agent review

Production code, defaults, native binaries and source projects are unchanged.
This is an isolated scientific study; no deployment or production acceptance claim.

## Repository coverage

Disjoint coverage: **12,186 passed, 298 skipped**. See
[test-results.json](test-results.json) for each retained log, SHA256 and count.
The remainder suite passed 11,320 / 293 skipped; Roads 530 / 5 skipped;
disturbed native matrix 99; treatment-soil partitions 230; new runtime gates 5; additional negative-flux accounting tests 2.
The runtime test module was added after remainder collection and is counted
separately. The 11 focused drainage tests overlap the remainder and are not added twice.

Commands use `wctl run-pytest`; native work and readers use `wctl exec weppcloud`.
Stub completeness passes. Broad-exception enforcement reports zero changed
production Python files. Whitespace checks and scoped documentation lint pass;
final documentation check is retained with closeout logs. Spelling normalization
was previewed without changes.

## Primary-agent self-review

This is a self-review, not an independent review.

- **Runtime applicability:** the simplified studies lack `wepp_ui.txt`, present in
  actual source projects and canonical Roads fixtures. Closed historical packages
  remain unchanged. This package records the limitation and adds a separately
  declared 192-case runtime bridge. Native banners and file inventories verify mode.
- **Independence:** old loam/holdout duplicate material properties. Three added
  specimens are distinct; report seven unique material profiles and all input aliases.
- **Physical interpretation:** conductivity, mineral-versus-lithic classification,
  restriction depth, native discretization and uncertainty in underlying geology
  are separate. Deepest emitted silt Ksat is below the computational cap. No endpoint
  is represented as a measured or universally correct bedrock conductivity.
- **Artifact integrity:** compare parsed consumed soils, retain strict buffer-only
  changes, verify nonsoil inputs, rehash exact binary and reused references, and
  check full daily WAT calendars. Keep source-precision sediment mismatch flags.
- **Metric compatibility:** frozen legacy records predate the additive
  `annual_mean_export_delta_kg` parser field. All stored metrics must match the
  newly parsed report exactly; the new audit field is retained. Native reference
  bytes must still match their hashes. No output drift or numerical tolerance is hidden.
- **Reproducibility:** native declarations and initial plan/package bytes are frozen.
  Runtime collection and final summarization have separate retained source identities;
  collection snapshots remain available even after reference-metadata handling was
  revised in the shared analyzer. No model result was rerun to improve agreement.

## Retained diagnostic failures

The initial staging stopped on header timestamps/source paths; a second preflight
identified duplicate historical loam/holdout properties. Both occurred before new
native outcomes. Revalidation compares material rather than generated comments and
requires every newly added specimen to be distinct.

The first runtime analysis could not pickle a dynamically imported worker before
parsing any case. A module-level worker resolves this; failed and successful analysis
directories are retained. Runtime collection was repeated after adding explicit
runtime/file-inventory checks and source snapshots; native simulations were not repeated.

The main reference preflight stopped on the additive parser audit field described
above. Its directory is retained as `analysis-reference-schema-preflight-failed/`.
The revised check compares every stored metric, accepts only that known added audit
field, and then reparses the complete matrix. A subsequent input-inventory preflight
found two enumerated `normalized-*.sol` intermediates emitted by the prior FSWEPP
template repair. Their exact known hashes are now checked; other unexpected files
still fail. That partial audit is retained as
`analysis-input-inventory-preflight-failed/`. Final focused checks pass all 16 existing tests, followed by 2 new negative-flux tests. These failures are harness/provenance
checks, distinct from the retained native report/ELEMENT/EBE accounting discrepancies.

## Evidence boundary

Raw native artifacts, logs, frozen declarations and large analysis tables live under
`/wc1/runs/ro/roads-drainage-validation-20261029-v2/`.
Portable comparisons and manifests are in this package. The report states final
control-reproduction and accounting counts. Budget discrepancies and lack of field
observations remain limitations of scientific acceptance, not failed repository tests.

The broader native audit found negative ELEMENT fluxes in newly tested no-traffic
source-drainage cases. The initial strict audit is retained under
`analysis-negative-sediment-preflight-failed/`. The final analyzer preserves their
signed diagnostics, marks their physical budget invalid and forces reconciliation
acceptance false; no value is clipped and no tolerance is relaxed. Valid nonnegative
budgets still use the original audited helper. Tests prove both behaviors.

Publication adjustment: the staging script's plan path now names
`prompts/completed/study_execplan.md`, so fresh reproduction works after plan
archival. This is the only difference from `executed-study.py` retained with the
native runs. Reference analysis verifies that archived executed script against the
frozen declaration. Scientific preparation/execution logic is unchanged; the
analysis source actually used is retained in `analysis-v1/executed-analyze.py`.
