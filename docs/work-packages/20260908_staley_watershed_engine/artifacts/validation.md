# Validation evidence

2026-09-09 UTC. Execution baseline:
`db03285e986c7d42afb65434429e02eff66a2b48`.

## Completed

- Local manuscript: visually checked equations 4–6 and Table 4 after rendering
  PDF pages 15–16 and 36. All six coefficient rows match. See
  [coefficient check](coefficient_check.md).
- Container: `wctl run-python docs/work-packages/20260908_staley_watershed_engine/artifacts/audit_watershed.py`
  passes support/grid/outlet/hash assertions and reproduces
  [recorded JSON](watershed_artifact_audit.json). WBT fixture root is
  `/workdir/weppcloud-wbt`; no fixture changes or new delineation.
- Container versions: rasterio 1.3.10, NumPy 1.26.0.
- `wctl doc-lint --path wepppy/nodb/mods/postfire_debris_flow`: zero errors/warnings.
- `wctl doc-lint --path docs/work-packages/20260908_staley_watershed_engine`:
  zero errors/warnings.
- `git diff --check`: passes.

## Numerical and API validation

- Owner approved N01–N04; accepted engine contract and ADR-0056 precede code.
- Final independent reviewer run of
  `wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_staley2017.py --maxfail=1`:
  **145 passed**, 9.30 s; two preexisting dependency deprecations.
- `wctl run-stubtest wepppy.nodb.mods.postfire_debris_flow.staley2017`:
  **Success: no issues found in 1 module**. Initial run caught a duration-key
  type mismatch; validated durations now explicitly convert to integer keys.
- `wctl check-test-stubs`: all stubs complete.
- `wctl run-python tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`:
  pass, one new production Python file scanned, zero broad handlers.
- `wctl run-python tools/code_quality_observability.py --base-ref origin/master --json-out /tmp/staley_engine_quality.json --md-out /tmp/staley_engine_quality.md`:
  observe-only report generated. Container lacks radon/eslint and the report
  does not produce working-tree addition deltas; no complexity claim is made.
- `wctl run-python docs/work-packages/20260908_staley_watershed_engine/artifacts/generate_examples.py`:
  emitted [synthetic_examples.json](synthetic_examples.json), six rows with
  independent 60-digit Decimal oracles and five explicit edge outcomes.
  For M1/15 T=.4,F=.6,S=.3,R=8: q=.776, x=2.578, p=.929432205755199;
  p=.5 inverse is 4.677835051546391 mm (18.711340206185564 mm/hour).
- [Independent correctness review](20260909_correctness_review.md): pass,
  zero unresolved findings. Reviewer verified 108 additional Decimal cases,
  source equations/table, and unmodified watershed fixtures.

## Full-suite gate

`wctl run-pytest tests --maxfail=1`: **7,959 passed, 72 skipped, 3,106 warnings**
in **791.10 s (13:11)**, exit 0. It collected 8,030 tests plus a collection skip
before the review regressions were added; the separate final focused run
validates the final engine and all 145 numerical tests after those corrections.
The full log was captured at `/tmp/staley_engine_full_pytest.log` during execution.
No full-suite failures were suppressed or tests deselected.

## Limits

Numerical examples are synthetic arithmetic evidence, not real-project scientific
validation. No predictor aggregation, climate adapter, production UI/NoDb/RQ,
run-state mutation or deployment is delivered by this bounded package.

## Closeout

Independent correctness findings are closed; container artifact reproduction,
API/stub checks, focused/full tests, scoped doc lint and whitespace checks pass.
Example rerun matches the committed-intended JSON byte for byte. Changes remain
in the working tree on the original branch; no deployment or push was performed.
