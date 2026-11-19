# Evaluation commands and retained outputs

Native worktree: `/workdir/wepp-forest-native-soil-capacity`.
WEPPpy documentation worktree: `/workdir/wepppy-native-soil-capacity`.
Evidence root: `/workdir/native-soil-capacity-evidence`.
Pin `PATH=/usr/bin:/bin:$PATH` for all native commands.

## Builds

Baseline source is default-branch commit
`7d4cf4b5ab24bbc825515d54f25a035062b826bb`. Candidate source is
`fd7e0a5a6526ae217a58eb5bb2c491d75273610d`. In separate clean task checkouts,
run `make -C src -j4 wepp`, then `make -C src -j4 wepp_hill`, then
`make -C src prepare_watershed_includes`. Do not overlap target-role builds.
Copy the baseline/candidate binaries to separate evidence directories before
rebuilding. The recorded compiler, hashes and input-source digest are in
`build-manifest.json`. The retained patch excludes generated executables.

## Reader tests

Use `/workdir/wepppy/.venv/bin/python -m pytest` as the pytest invocation.
On baseline, run `tests/test_native_soil_input_capacity.py -k eleventh
--basetemp=/workdir/native-soil-capacity-evidence/baseline/probe -q` using the
candidate test file. Expect the decisive regression to fail: six layers rather
than nine. Keep its compiled reader for state comparison.

On candidate, run `tests/test_native_soil_input_capacity.py
--basetemp=/workdir/native-soil-capacity-evidence/candidate/probe -q`.
Expect 40 passing tests. Final targeted result is `probe-final.log`.
The full suite was collected before the last seven targeted cases were added;
those seven are covered by the final targeted run.

Run the state comparison using the compiled `soil-reader0/reader` executables:

    python tools/evaluate_soil_reader_states.py \
      --baseline /workdir/native-soil-capacity-evidence/baseline/probe/soil-reader0/reader \
      --candidate /workdir/native-soil-capacity-evidence/candidate/probe/soil-reader0/reader \
      --output /workdir/native-soil-capacity-evidence/state-parity

## Full runs

Run the hillslope tool with the retained Zepol source fixture:

    python tools/evaluate_soil_input_capacity.py \
      --baseline /workdir/native-soil-capacity-evidence/baseline/wepp_hill \
      --candidate /workdir/native-soil-capacity-evidence/candidate/wepp_hill \
      --output /workdir/native-soil-capacity-evidence/hillslope-v3 \
      --zepol /workdir/wepppy-native-soil-capacity/docs/work-packages/20261118_native_soil_input_capacity/artifacts/zepol_raw_10.sol

Run `tools/evaluate_soil_input_mofe.py` with the same binary options and
`--output /workdir/native-soil-capacity-evidence/mofe` for three OFEs over
sixteen years. These tools require fresh output directories and do not overwrite
evidence. Use new output paths when repeating.

Run complete watershed cases with fresh paired hillslope pass files:

    python tools/evaluate_soil_input_watershed.py \
      --evidence /workdir/native-soil-capacity-evidence \
      --output /workdir/native-soil-capacity-evidence/portable-watershed-final

The tool checks native completion markers, requested simulation years, finite
channel records and original-input artifact parity. The older
`tools/replay_delicate_game_fixture.py` also regenerated 301 hillslopes per build,
but that fixture lacks watershed routing inputs. Its zero exit status does not
establish watershed completion; retain only its hillslope parity evidence.

## Other gates

From the native worktree, run `tools/smoke_wepp_binary_host.sh <binary>` for both
candidate roles, `python tools/run_hillslope_watchlist.py --binary <candidate-hill>`,
`python tools/check_ablation_artifact_policy.py`, and `python -m pytest -q`.
From WEPPpy run `tools/check_wepp_binary_provenance.sh <candidate-wepp>
<candidate-hill>`; both must use the system loader and libgfortran.

Use `wctl --project-dir /workdir/wepppy-native-soil-capacity doc-lint --path
 docs/work-packages/20261118_native_soil_input_capacity` for the package, and
`markdown-doc lint --path docs/specs/source/input.for.md` from native root.
The explicit project directory prevents the installed wctl wrapper from linting
the unrelated shared checkout.
