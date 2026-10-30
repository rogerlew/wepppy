# Buffer study validation and reproduction

Complete: 24 native runs; **12,168 tests passed, 298 skipped, no failures**.

## Execution evidence

- 24/24 native cases complete; consumed inputs and native outputs rehashed.
- Four unchanged controls reproduce all seven prior native outputs byte-for-byte.
- Eight zero/+1 mm pairs reproduce all seven native outputs byte-for-byte.
- All expected 24 computational depths confirmed by actual WAT artifacts.
- All runs cover 5,844 days × three OFEs; all budget fields finite.
- Every treatment preserves road/fill soil objects and all buffer material fields;
  only buffer kslast and the last cumulative depth can change.
- All 24 boundary water-transfer and sediment report/ELEMENT checks pass.
- No beyond-precision EBE discrepancies in this panel.
- Independent DuckDB aggregation reproduces all 24 sediment and water budgets.
- Upstream output equality was tested and rejected in 14/24 cases. This is retained
  as a finding, not relabeled as invariant or hidden by a tolerance.
- All 12 alternative-drainage cases meet the factor-ten export band; no production
  candidate is accepted without physical and broader validation.

## Retained attempts

Root: `/wc1/runs/ro/roads-buffer-drainage-20261029`.
Stage, native execution and all per-case accounting succeeded. The first analysis
under `analysis/` stopped at its exact upstream-output equality check after writing
all 24 validated per-case results. Its executed source and partial artifacts remain.
`reconciliation-v2/` rehashes those records/native files, verifies reference inputs,
quantifies every upstream difference and records control/reconciliation counts.
It does not rerun or modify native results. The source audit identifies a native
routing coupling mechanism; water/state differences are not fully traced.

## Reproduction commands

From repo root, with host access to `/workdir/wepp-forest` Git objects and the
retained preceding study inputs. Staging, simulation and analysis refuse existing
destinations. Use a fresh root for a repeat.

```bash
python3 docs/work-packages/20261029_roads_buffer_drainage/artifacts/experiment.py stage --root /wc1/runs/ro/roads-buffer-drainage-UNIQUE
wctl exec weppcloud python docs/work-packages/20261029_roads_buffer_drainage/artifacts/experiment.py run --root /wc1/runs/ro/roads-buffer-drainage-UNIQUE
wctl exec weppcloud python docs/work-packages/20261029_roads_buffer_drainage/artifacts/experiment.py analyze --root /wc1/runs/ro/roads-buffer-drainage-UNIQUE
```

The last command is expected to stop at the retained upstream-equality failure
on the first sand depth-minus case. This frozen diagnostic remains executable;
complete the explicitly qualified accounting with:

```bash
wctl exec weppcloud python docs/work-packages/20261029_roads_buffer_drainage/artifacts/reconcile.py --root /wc1/runs/ro/roads-buffer-drainage-UNIQUE
wctl exec weppcloud python docs/work-packages/20261029_roads_buffer_drainage/artifacts/summarize.py --root /wc1/runs/ro/roads-buffer-drainage-UNIQUE
```

Summarize writes the portable evidence to its own artifacts directory. Native
source snapshots and input/output SHA-256 values are retained in declaration and
result records. Exact reader identities are retained in reader-provenance.json.

## Tests

Focused treatment tests: **15 passed**. Coupling diagnostics: **2 passed**.
The latter test file was added after the broad sweep collected its tests, so its
two cases are supplemental coverage, not included in that sweep's count.

Fresh full-suite coverage uses the established disjoint groups: Roads, Disturbed
matrix, nine soil-treatment selectors, and the repository remainder. The treatment
selectors cross 9002/9005, single/mofe, thinning/not-thinning (eight sets of 27),
plus `not 9002 and not 9005` (14). All deselections are covered elsewhere.

```bash
wctl run-pytest tests --ignore=tests/nodb/mods/disturbed/test_treatment_soil_artifacts.py --ignore=tests/disturbed/test_disturbed_matrix.py --ignore=tests/roads --maxfail=1
```

Final disjoint coverage:

| Group | Result |
|---|---|
| Roads | 530 passed, 5 skipped |
| Disturbed matrix | 99 passed |
| Soil-treatment selectors | 230 passed |
| Repository remainder | 11,307 passed, 293 skipped |
| Post-collection reconciliation tests | 2 passed |

No test results from the preceding study are reused. Native runs and independent
SQL checks are additional evidence, not pytest counts. The remainder completed in
25 minutes 47 seconds. [Machine-readable counts and log hashes](test-results.json)
retain the evidence. Logs are under the execution root's logs directory.

Package/PROJECT_TRACKER/tests-AGENTS doc lint, new-package spelling previews,
`git diff --check`, `wctl check-test-stubs`, and changed-production broad-exception
enforcement pass. The latter observes zero changed production Python files.
Primary-agent self-review is retained in [review.md](review.md); no independent
subagent review was requested.
