# Execution commands and receipts

Native checkout: `/workdir/wepp-forest-release-20261009`; baseline `6a6621e4`.
External lane trees: `/workdir/watershed-physical-water-repair-20261021`.

- `PATH=/usr/bin:/bin /workdir/wepppy/.venv/bin/python -m pytest -q tests/test_component_reconstruction.py tests/test_channel_state.py tests/test_execution_calendar.py`: 88 passed on baseline.
- New `tests/test_physical_water.py` on baseline: 15 failed, six passed; retained full output in `baseline-defect-tests.txt`.
- Candidate `tests/test_component_reconstruction.py tests/test_physical_water.py -k 'not channel_local'`: 92 passed, six deliberately deselected channel cases.
- Isolated lanes build using `make -B wepp` or `make -B wepp_hill FC=/usr/bin/gfortran LINKER=/usr/bin/gfortran`; build logs remain alongside each lane.
- `tools/physical_water_case.py DEST --layout upper60 --mode daily --years 2`, then 261021 hill and watershed stdin cards: both phases complete the configured two years.
- External `replay_hill_lanes.py`: six groundwater and four allocation cases, all 44 years, complete successfully. `hill-lane-results.json` records executable hashes and final rows.
- External `replay_routing_lanes.py`: isolated flat, positive-local experiment and combined diagnostic candidates; paired phases use the same watershed-capacity executable, which supports both modes. Off/on observations are compared separately.

One generator edit initially ran from the lane `src/` directory and failed with
FileNotFoundError before any edit; it was reapplied in the native root. The
subsequent build was unaffected. No claim relies on that failed edit command.

Final candidate v4: full native suite **361 passed, four strict expected failures**
(the open channel-local defect), two existing tarfile warnings. Twelve watchlist
cases and both profile smoke checks pass. Twenty-nine paired cases pass exact
WAT/PASS/channel dates and transfer checks: ten two-year controls, eighteen
44-year audit configurations and one 400-year hourly 60/40 control (146,097 days).
See `final-build-provenance.json`, `final-validation.json` and gate logs.

The first 400-year fixture attempt failed after year 44: changing management
rotation count did not supply sequential annual records. The generator now writes
all requested annual records; the second attempt completes all 400 years. This
was fixture construction, not a new calendar defect. Receipts preserve both.

`tools/physical_water_solver_probe.py DEST` independently integrates full spatial
Manning geometry from actual node discharge and compares it to the native MC
algebraic inventory. The fixed-grid/positive-coefficient control still fails
geometric closure, so replacing only the endpoint storage estimator is insufficient.
An initial diagnostic script stopped on an ambiguous source anchor before compile;
the successful version uses a unique newline-anchored insertion.

MC-preserving continuation:

- `python tools/mc_continuity_probe.py DEST`: 16 actual MC4/5 controls, full per-step recurrence/state/publication observations; strict dimensions and finite-record validation.
- `python tools/mc_cascade_probe.py DEST`: eight two-channel cases using actual WSHCQI and WSHCHR; retained receipts distinguish daily and rate transfers.
- `python tools/mc_interior_state_probe.py DEST`: explicit legacy-guard ablation versus current eligibility, fixed positive-coefficient interior-pulse control.
- `PATH=/usr/bin:/bin python -m pytest -q tests/test_channel_state.py -k interior`: before source correction six failed/two passed; after correction all eight pass.
- Final targeted source/state/component suite: 165 passed, four strict expected failures.
- Full suite with `WEPP_GUARDED_BINARY=/workdir/watershed-physical-water-repair-20261021/mc-guard-candidate/src/wepp`: 369 passed, four expected failures, two existing warnings; 567.32 seconds. This elapsed time is not a controlled performance comparison.
- Both final profile smokes and the 12-case full-period watchlist pass.
- `replay_mc_guard.py` and `validate_mc_guard.py`: all 29 fresh paired cases complete and pass date/transfer validation; no original run mutated.

The MC guard source changes only recurrence eligibility. The operator explicitly
rejected imposing geometric storage equality; the earlier solver-probe discrepancy
is a diagnostic difference of storage interpretations, not a standalone MC
mass-loss finding. See `mc-continuity-findings.md` and `repair-handoff.md`.

Documentation gates: scoped WEPPpy package/ADR/project lint and root-size checks
pass. For the native checkout, `wctl doc-lint` resolves the WEPPpy root (relative
paths checked zero files; an absolute outside-root path panicked). Direct canonical
`markdown-doc lint --path ...` from the native root validates README, changelog,
contract, four source specs and incident docs with zero errors/warnings. This is
a wrapper scope limitation, not a skipped native-doc gate.

Native source/portable fixtures/evidence checkpoint committed as `22133f0c9` on
the verified remote-default branch. Source/doc whitespace checks pass; retained
raw fixture decks and native log/diff evidence preserve their original whitespace
and are excluded from that formatting gate. All 44 native incident checksums
were verified against staged git blobs after canonical LF normalization of CSVs.


## MC interface/reference checkpoint e6dc19008

Native checkout: `/workdir/wepp-forest-release-20261009`; isolated paired build:
`/workdir/watershed-physical-water-repair-20261021/mc-reference-candidate-v5`.
Build watershed then hillslope sequentially with `make -B wepp` and
`make -B wepp_hill`, both using `FC=/usr/bin/gfortran LINKER=/usr/bin/gfortran`.
Retained build logs pin flags; source manifest and binary hashes are in
`mc-reference-v5-manifest.json` and `mc-reference-v5-validation-receipt.json`.

From the native checkout:

    PATH=/usr/bin:$PATH WEPP_GUARDED_BINARY=/workdir/watershed-physical-water-repair-20261021/mc-reference-candidate-v5/src/wepp /workdir/wepppy/.venv/bin/python -m pytest -q
    PATH=/usr/bin:$PATH /workdir/wepppy/.venv/bin/python -m pytest -q tests/test_mc_fixed_point.py tests/test_mc_reference_lifecycle.py
    python tools/run_hillslope_watchlist.py --binary /workdir/watershed-physical-water-repair-20261021/mc-reference-candidate-v5/src/wepp_hill
    tools/smoke_wepp_binary_host.sh /workdir/watershed-physical-water-repair-20261021/mc-reference-candidate-v5/src/wepp
    tools/smoke_wepp_binary_host.sh /workdir/watershed-physical-water-repair-20261021/mc-reference-candidate-v5/src/wepp_hill
    python tools/mc_continuity_probe.py NEW_UNUSED_DESTINATION
    python tools/mc_cascade_probe.py ANOTHER_UNUSED_DESTINATION
    python tools/check_ablation_artifact_policy.py

Full suite: 490 passed, two existing tarfile warnings. Expanded final reference
suite: 92 passed, covering 30 added mode cases after the full-suite collection.
Final collection is 520 tests; all covered. The exact formerly failed 100-year
gate also passes independently in 580.64 seconds within its unchanged 900-second
timeout. Both ELF interpreters are `/lib64/ld-linux-x86-64.so.2`.

Full 29-pair replay/validation commands and large raw outputs are retained in
`replay_mc_reference_v5.py`, `validate_mc_reference_v5.py` and
`mc-reference-v5-replays/` under the external experiment root. Repository
receipts retain complete date/count validation including 400 years. Native
required tests and fixtures do not depend on those supplementary directories.

Diagnostic destination paths must not already exist.
