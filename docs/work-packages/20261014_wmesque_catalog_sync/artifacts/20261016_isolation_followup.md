# M7 isolation follow-up — 2026-10-16

Hosted run [38825109720](https://github.com/rogerlew/wepppy/actions/runs/38825109720)
passes stubtest, baseline (10,671 passed, 329 skipped), and all five repeat suites.
No randomization plugin is installed; these are unchanged-order repeats.
The final per-file/state-scan phase failed; cleanup and diagnostic upload worked.

## Confirmed causes and corrections

- Six standalone test files passed pytest but the checker crashed afterward:
  `hasattr` on lazy `wepppy.nodb.mods` imported unrelated modules while inspecting
  singleton caches. Read module dictionaries without invoking lazy imports.
- Snapshot boundaries included pytest startup/shutdown, classifying normal
  initialization as pollution. Bracket collection/execution inside the session
  lifecycle. Keep collection-time stub/environment leak detection.
- Fileless Cython/SWIG/DuckDB helpers and Pint/Rasterio import defaults require
  bounded classification; see [checker contract](../../../dev-notes/test-isolation.md).
  Normal imports are not replacements; changed/replaced existing state remains
  a finding. These exceptions are heuristics, not authentication of module origin.
- Five report files, the Daymet file, and a soil utility file installed persistent fake dependencies
  during collection. Remove those legacy stubs; use installed canonical libraries.
- Two real WBT tests, opt-in during the broad suite, failed standalone. The
  TerrainProcessor helper omitted strict unresolved-depression failure while
  requesting no filling. Forward the existing flag per
  [ADR-0095](../../../adrs/ADR-0095-terrain-helper-strict-least-cost-breach.md);
  preserve diagnostic validation and artifacts.
- Identical worker failures could produce an overall clean result. Nonzero
  executions now remain findings regardless of baseline suppression; internal
  errors return 2. Missing requested snapshots fail explicitly. CI requests
  structured JSON so worker exception traces survive in the job log.

## Validation

Focused report/Daymet/helper/WBT/tool checks: 142 passed. Expanded checker
regressions and broader topo checks: 178 passed, four opt-in skips, including real subprocess tests that prove persistent
collection stubs/environment leaks remain visible and a clean pytest lifecycle
is not pollution. The earlier 142-test run explicitly executed both real-WBT
cases that are opt-in during a directory-wide run. Matching runner-02 isolation passes one combined iteration and all 15 per-file
checks (24.04-second combined run, no state findings), including the real WBT
module and checker negative controls. The final standalone checker regression
run passes 20 tests, including zero-work rejection and unsuppressible error
exit behavior. Broad-exception enforcement and stub completeness pass; workflow
generation and documentation checks pass. A broad collection-only audit completed 703 per-file collections without execution
errors. It ran while native-module recognition was being refined, so it is not a
clean final-source acceptance receipt. Its findings exposed one additional
persistent `deprecated` stub (removed), Cython/Passlib import objects, and bounded
Threadpoolctl/Scikit-learn/Pyogrio/Fiona environment defaults. Two app-importing tests
now scope `ASSET_VERSION` during collection. Additional focused checks pass
98 tests; the expanded checker regressions pass 27 tests. All 36 files flagged by
the audit pass the final-source collection recheck with `issues: []`. The four
additional soil/web/checker files also pass one combined execution and every
per-file execution with `issues: []` (24.33-second combined run). Collection-only diagnosis
is not acceptance of test bodies. Runner-02's owned temporary stack, volumes,
and local image were removed; no project containers remain.
Full hosted isolation acceptance remains open; no thresholds or repetitions changed.
