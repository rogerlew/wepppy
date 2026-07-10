# Validation Summary - Management Rotation Synthesizer Hardening

## Incident Scan

The source directory contains 119 each of `.man`, `.run`, `.slp`, and `.err`.
All 119 error files match `ncrop +read as`; the observed counts are:

    34:52  35:26  36:10  37:5  38:4  39:5  40:1  41:3
    42:4   44:1   45:2   46:1  47:1  48:2  49:1  50:1

The pre-repair focused test failed as intended: p3733 produced `ncrop=50` and
the distinct-plant preflight did not exist.

## Automated Tests

`wctl run-pytest tests/wepp/management/test_rotation_stack.py -q`

- Result: 8 passed.
- Covers existing end-to-end behavior, residue plant prefixing, setup-year merge,
  the exact p3733 schedule, combined spring/fall operation order, round-trip
  parsing, and the more-than-20-distinct-plants pre-write failure.

`wctl run-pytest tests/wepp/management -q`

- Result: 21 passed.

`wctl run-stubtest wepppy.wepp.management.utils.rotation_stack`

- Result: success, no issues in one module.

`wctl check-test-stubs`

- Result: passed.

## Generated Management and Binary Replay

The exact one-canola-plus-sixteen-oats fixture generated:

    ncrop=3
    nop=10
    nini=1
    nseq=17
    nscen=17
    sim_years=17

The temporary run used source p3733's slope and parent p621's soil/climate with:

- Binary: `/home/workdir/wepppy/wepp_runner/bin/wepp_260430_hill`
- SHA-256: `3b2fdd2b7a9e264b84f1e7b161dfb0730d49d3cb652218139efeb3ba17d7a160`
- Incident `ncrop` error present: no.
- Successful-completion marker present: no.
- Next binary validation:

      HMAX <= 0.0 FOR CROP INDEX 2 (name=L179_wee)
      INVALID PLANT PARAMETER (hmax=0.0000E+00, cuthgt=0.0000E+00)

This proves the wired synthesizer failure is resolved. The remaining error is
present in the source fixture and requires a valid source-management correction.

## Repository Gates

`python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`

- Result: passed, net changed-file broad-catch delta zero.

`.venv/bin/vulture wepppy/wepp/management/utils/rotation_stack.py wepppy/wepp/management/managements.py --min-confidence 80`

- Result: passed with no findings after removing stale debug imports.

`wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260710_management_rotation_synth_hardening --path wepppy/nodb/mods/ag_fields/README.md`

- Result after final closeout and ExecPlan archival: 10 files, zero errors and
  warnings.

`git diff --check`

- Result: passed.

`wctl run-pytest tests --maxfail=1`

- Result: unrelated baseline failure after 2,072 passed, 41 skipped, and 35
  warnings in 320.77 seconds.
- Failure:
  `tests/nodb/test_batch_runner.py::test_run_batch_project_does_not_delete_workspace_when_rmtree_disabled`.
- Isolated reproduction: failed identically. `clear_nodb_file_cache` resolves
  `/wc1/batch/batch-demo/runs/leaf-run` outside the test's patched
  `batch_runner_mod.get_wd`. No implicated Batch Runner file is changed here.

## Verdict

The original management synthesizer milestone passed its scoped release gate.
The exact overflow was fixed with hermetic regression coverage and
current-binary evidence; the package was then reopened for the source parameter
under the ADR-governed milestone below.

## Reopened ADR-0016 Milestone

Inventory of the preserved Jim-interface sources found the same `L179_weed`
placeholder in all ten managements: `hmax=0`, `cuthgt=0`, `rdmax=0`, and
`xmxlai=0`. Reference inspection shows it is used by residue-addition operations,
not as an active yearly or initial plant.

Focused validation:

- `tests/nodb/mods/test_ag_fields_backend_contract.py`: 22 passed before the
  legacy-state compatibility assertion was added.
- Final combined backend and rotation regression: 31 passed.
- Exact ingestion covers 2017.1 and 98.4, byte-preserved source, header comments,
  additive provenance, active-plant exclusion, and 17-year synthesis.
- `wctl check-test-stubs`: passed.
- Broad-exception gate: passed with net delta zero.

Current-binary replay after applying the ingestion helper:

    normalizations=17 (canonical result retains one L179_weed)
    ncrop=3, nop=10, nini=1, nseq=17, nscen=17, sim_years=17
    residue hmax=0.00001 m
    ncrop error=false
    HMAX error=false
    success marker=false
    returncode=-8
    SIGFPE at /workdir/wepp-forest/src/frcfac.for:184

The height fallback therefore meets its observable contract. The subsequent
random-roughness failure is independent and remains explicitly out of scope.

Final repository-wide gate:

- Collected 4,863 tests (2 collection skips).
- Stopped at the known unrelated Batch Runner fixture-path failure after 2,074
  passed and 41 skipped in 309.82 seconds.
- The same failure was independently reproduced earlier in this package; no
  Batch Runner source or test file is changed by either milestone.
