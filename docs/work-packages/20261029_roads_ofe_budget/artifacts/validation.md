# Roads OFE study validation

Complete: 66 native study runs; full repository coverage **12,151 passed, 298 skipped, no failures**.

## Native artifacts and accounting

- 66/66 runs completed, consumed-input hashes unchanged, all native output hashes
  rechecked; exact modern and legacy binary hashes retained.
- 66 complete WAT calendars: 5,844 days × three OFEs each.
- 60 modern ELEMENT/WAT/EBE/PASS datasets parsed with existing Rust-backed readers.
- Six complete factorials pass fixed-field, independent-toggle, 200 mm boundary,
  deeper-material and matched-management/climate/geometry checks.
- Six all-on endpoints reproduce seven native output files each byte-for-byte from
  the preceding roles study; old files independently rehashed before comparison.
- Surface/lateral transfer checks pass for all 60 modern budgets.
- Terminal ELEMENT/report precision checks pass for 53/60. Seven failures and
  22 EBE event discrepancies remain explicit. They limit attribution; they are
  not reclassified as successful reconciliation.
- Plot visually inspected; values/tables reproduced from portable result JSON.

[Source semantics and bounds](output-semantics.md), [acceptance counts](acceptance.json),
[run hashes](run-evidence.json), [reader identities](native-reader-provenance.json),
and [prior reproduction](prior-reproduction.json) retain the evidence.

## Attempts and recovery

The first stage under `roads-ofe-budget-20261029` failed because the container
cannot access `/workdir/wepp-forest` Git objects. It remains intact. Staging on the
host into fresh `roads-ofe-budget-20261029-v2` succeeded. Native batch `factorial-v1`
then completed all 66 cases without retries or failed native executions.

Analysis v1 rejected ISO date strings passed as integer reader start years. V2
corrected the explicit year conversion, then stopped on an EBE/ELEMENT mismatch.
The exact native source audit established separate report/ELEMENT routing branches.
V3 retains reconciliation booleans and dated mismatch values without widening any
precision bound. No native result was overwritten or rerun to obtain agreement.
Each analysis directory retains its executed accounting source and partial records.

## Reproduction

Use a fresh root for staging/running; the harness refuses existing destinations.
Staging requires host access to the native Git repository. Simulation and analysis
use the canonical container environment. Existing frozen prior-study assets must
be available at the paths recorded by `study.py`.

```bash
python3 docs/work-packages/20261029_roads_ofe_budget/artifacts/study.py stage --root /wc1/runs/ro/roads-ofe-budget-UNIQUE
wctl exec weppcloud python docs/work-packages/20261029_roads_ofe_budget/artifacts/study.py run --root /wc1/runs/ro/roads-ofe-budget-UNIQUE --workers 6
wctl exec weppcloud python docs/work-packages/20261029_roads_ofe_budget/artifacts/accounting.py --root /wc1/runs/ro/roads-ofe-budget-UNIQUE --destination /wc1/runs/ro/roads-ofe-budget-UNIQUE/analysis-v3
wctl exec weppcloud python docs/work-packages/20261029_roads_ofe_budget/artifacts/summarize.py --root /wc1/runs/ro/roads-ofe-budget-UNIQUE --destination /tmp/roads-ofe-portable-existing-directory
```

`summarize.py` expects `analysis-v3`, writes portable evidence to an existing
directory, and rechecks the preceding roles output identities. The checked-in
figure and CSV are generated artifacts, not manually edited scientific results.

## Repository checks

Focused: `wctl run-pytest tests/tools/test_roads_ofe_budget.py --maxfail=1`:
**16 passed**. Coverage includes malformed/missing/duplicate/nonfinite records,
unequal-area water transfers, independent report and event comparisons, explicit
unreconciled diagnostics, treatment leakage and deeper-horizon preservation.

The serial full-suite invocation was deliberately interrupted after all 99
Disturbed matrix tests passed, to avoid duplicating the heavy groups run in
parallel. Its final partial summary is 527 passed / 28 skipped; those extra
pre-Disturbed passes are not added to the disjoint coverage total. The remaining
groups follow the preceding study's full-suite partition:

| Group | Result |
|---|---|
| Disturbed matrix, completed within the serial sweep | 99 passed |
| `tests/roads --maxfail=1` | 530 passed, 5 skipped |
| Soil-treatment artifacts, nine disjoint selectors | 230 passed |
| Remaining repository | 11,292 passed, 293 skipped |

Treatment selectors cross `9002`/`9005`, `single`/`mofe`, and
`thinning`/`not thinning` (eight groups of 27). The ninth selector is
`not 9002 and not 9005` (14). Deselections are covered by the other groups.

```bash
wctl run-pytest tests --ignore=tests/nodb/mods/disturbed/test_treatment_soil_artifacts.py --ignore=tests/disturbed/test_disturbed_matrix.py --ignore=tests/roads --maxfail=1
```

Logs are retained under the execution root's `logs/`. Focused test results are
already included in the repository remainder and are not added twice.
Doc lint passes for the package, PROJECT_TRACKER.md and tests/AGENTS.md;
`git diff --check` and changed-production broad-exception enforcement pass.
Spelling previews find no changes in the new package; unrelated suggestions in
existing root/test guidance were left alone.

Machine-readable counts and log hashes: [test-results.json](test-results.json).
The final repository remainder took 25 minutes 19 seconds.
Primary-agent [self-review](review.md) completed; no independent subagent review
was requested. Scientific accounting limits remain as reported.
