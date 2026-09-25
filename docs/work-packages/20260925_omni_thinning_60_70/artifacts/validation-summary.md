# Validation summary

Starting revision: cf6437095. Contract ancestor: 9ed739875.
Implementation candidate: 2d0891398 (unchanged production/test bytes throughout validation).

## Completed evidence

- red-tests.log: missing thinning_60_90 fails catalog resolution before asset edits.
- focused-tests.log: 308 passed, 12 subtests in 41.93s. Real source parsing,
  single-OFE management preparation, mixed eligible/ineligible MOFE synthesis,
  prepared management readback, canonical archive/restore and catalog snapshot.
  Existing Omni parser/mode and browse/download coverage included.
- frontend-tests.log: 112 suites, 913 tests pass. All six canopy choices hydrate
  and serialize; new rows retain 40/93 defaults.
- lint.log and build.log: frontend lint and canonical container bundle rebuild
  pass; ignored bundle hash and 60/70 descriptor readback retained.
- compatibility.json: all 16 legacy thinning assets byte-identical to base;
  every existing entry in five catalogs and CSV bytes preserved. Each new file
  changes only initial cancov; all other source bytes equal matching 40% source.
- exceptions.log: no added broad catches.
- broad-tests.log: all 230 real soil artifact cases passed, including all 32 new
  60%/70% cases. soil-test-manifest.log records the exact case inventory.

## Broad-suite outcome

Required `wctl run-pytest tests --maxfail=1`: 5,326 passed, 54 skipped, one
failed in 1977.31s. Failure is
`test_run_hillslopes_uses_mofe_timeout_for_continuous_hillslopes[False-60]`: expected 60,
actual 120. Unchanged runner and accepted ADR-0072 require 120.
`timeout-baseline-identity.json` proves runner/test/ADR blobs identical at package
base and candidate. This independently reproduced baseline failure also occurred
in the preceding soil-lookup package. No changed thinning code is invoked by the
failing stubbed runner test. Later tests were not run; full-suite success is not
claimed. Repository maintainers own the unrelated test-expectation follow-up.

Both independent review artifacts record zero package findings and local
code-delivery approval. Production/live acceptance remains separate.

## Quality telemetry

Observe-only quality telemetry passes; radon is
unavailable. Production JavaScript adds two option entries without changing
function complexity or adding runtime machinery. CRLF-aware git whitespace
check passes outside new .man copies. CSV retains existing CRLF intentionally;
new 93% ground files retain the 40% sources' trailing space and final blank line,
so raw whitespace check reports those inherited bytes. No normalization applied.

## Claim boundaries

Locally validated generated management and soil inputs.
Retained command logs have trailing whitespace normalized without changing results.
Archive state labels are artifact snapshots, not live lifecycle execution. No changed writer/path/lifecycle or
model formulas. New 60/70 soil cases use existing generic thinning lookup rule.
No live browser, production deployment, existing-project mutation, fresh model
execution or regenerated scientific reports claimed. Operator owns those release
gates; saved 65% hydration and all old IDs/files remain supported.
