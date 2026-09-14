# Validation — milestone-1 source audit

2026-09-14, base `c81635b43804a11642e6c777ae725aa4a7fa7b78`.

The unchanged thickness helper was evaluated against three frozen CSV fixture
sets and live core records read within a single SQLite transaction. Counts,
hashes, grid inspection and limits are retained in `source_inventory.md`.
This is exploratory evidence, not production policy or builder regression tests.

`wctl doc-lint --path docs/work-packages/20260914_staley_m3_integration`
passed initially for eight files, zero errors/warnings; final expanded package
validation passed for ten files, zero errors/warnings. ADR-0067 lint passed
for one file with zero errors/warnings.
`git diff --check` passed. Spelling preview for the new inventory, proposal and
ADR produced no differences.

No runtime code changed. Python/npm suites, real WBT/RQ execution, source
acquisition, soil build parity and archive/browser acceptance have not run in
this increment. Those remain required implementation milestones.

## Depth-policy investigation

Ran `.venv/bin/python docs/work-packages/20260914_staley_m3_integration/artifacts/depth_policy_experiment.py`.
Four policies evaluated against all three frozen source panels and the live
cache in one read transaction; results retained in `depth_policy_results.json`.
Sixteen analytical cases pass. All-policy duplicate-ID conflict checks cover
differences confined to material, horizon names and reported thickness, as well
as endpoints. Pair audit checks retain original IDs and distinguish duplicate
source records from physical intervals. Authentic-data results were unchanged
after correcting the research normalization defect found by both reviewers.

This is an isolated research script, not an implemented production adapter.
No full runtime suite or soil-builder parity is claimed by these assertions.
Both reviewers independently rechecked the corrected experiment; details in
`20260914_depth_policy_reviews.md`. Scoped doc lint passes for the expanded
package, ADR-0067 and canonical production-M3 proposal; `git diff --check` passes.
