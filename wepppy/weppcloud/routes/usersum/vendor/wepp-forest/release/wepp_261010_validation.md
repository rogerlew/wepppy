# WEPP 261010 Release Validation

2026-10-10. Source `7471bb5e981d14d0b8c1cdb88a16af305aed1b67` on verified
remote-default branch `wepp_260430_negmeltfix_comparator`. Roger authorized
release/vendoring and withdrawal of never-deployed 261009 from WEPPpy.
No production deployment or general project-default switch was performed.

## Identity and Equivalence

| Binary | SHA256 |
| --- | --- |
| wepp_261010 | 1dd1ca75cf53f9a0606cf5a598312d4e680e161df631156360d4a20dbcb6f17e |
| wepp_261010_hill | d8ea3a07a29ef1e754c5362bd7931cc3a93486d75faa32df5c5f2e821c22d698 |

Both binaries are byte-identical to the scientifically validated candidate
after `objcopy --strip-debug --remove-section=.note.gnu.build-id`. Executable
code and runtime data are not filtered out of this comparison. Original
candidate hashes and both normalized hashes are retained in
[candidate-equivalence.json](wepp_261010_validation/candidate-equivalence.json).
This supports applying the completed Topanga, Rattlesnake, mutation, disturbed
and Cedar evidence to this release. It is supplementary provenance evidence,
not a mandatory dependency on a private candidate directory.

No Fortran or active capacity-include changes occurred after the source commit.
The runtime banner remains 2020.500. The existing paired component-v3 native
reader and compositors are unchanged.

## Required Gates

- Clean sequential system-gfortran dated build: pass.
- Both Forest host smokes: pass; all 12 committed-resource watchlist cases pass.
- Post-build `python -m pytest -q`: 163 passed, two existing warnings.
- Ablation artifact policy and runtime provenance: pass. Both loaders are
  `/lib64/ld-linux-x86-64.so.2`; no non-system loader/runtime is introduced.
- Post-vendor provenance and both host/container smokes: pass.
- WEPPpy runner/output/interchange: 114 passed, one existing missing-fixture
  skip, two warnings. The skipped test lacks its pass_pw0 dataset.
- Fresh release disturbed matrix: 99 passed (96 simulations plus three
  completion checks); all 768 outputs exactly match the validated candidate.
- Report freshness, route coefficients and Usersum rendering: 63 passed.
- Scoped documentation lint and whitespace checks: pass.

The first bare Forest collection failed on archived research modules and
duplicate test names. `pytest.ini` now declares the maintained `tests/` suite
as default discovery; every maintained test runs, including the new captured
normalization cases. Research scripts remain explicitly runnable. No numerical
assertion was weakened. The full unrelated WEPPpy suite was not run for this
binary/publication handoff; the affected runner/interchange/report suites were.

## Additional Generated Evidence

The exact release pair regenerated 140 hillslopes for 1980-2024 and completed
all 45 years in plain, Roads additive and AgFields weighted watershed cases.
Hillslope conversion accepted 2,301,180 records with zero rejection. Roads
doubled the selected component volume from 195011.111 to 390022.222 m3;
the 0.3/0.7 weighted AgFields combination preserved 195011.111 m3. These are
interface replays, not calibrated scenario predictions. Input hashes, receipts,
full-period audit and summaries are retained; raw runs reside at
`/wc1/holdouts/wepp-261010-pass-validation-v2`.

An optional extra committed-fixture replay is **unavailable, not passed**:
`delicate_game_pw0` lacks pw0.str, pw0.chn and pw0.imp. Its 301 fresh hillslope
runs succeeded, but its watershed could not start. No private substitute or
fabricated topology was introduced. The fixture README and diagnostic now
state the limitation. This attempt does not replace or modify the required
gates above; the existing static fixture regressions still run.

Other retained tooling attempts: an initial integration invocation used a
Python installation lacking the bulk native conversion export; an overlapping
retry was rejected by the creation guard. The supported project venv completed
the fresh v2 study. An initial post-vendor pytest selector named a nonexistent
file; the corrected actual directories produced the 114-pass result. None of
these failed invocations is recorded as a pass or hidden by output relabeling.

## Commands

From Forest:

```bash
TARGET_TAG=261010 COMPILER=/usr/bin/gfortran tools/build_wepp_dated_release.sh
make -C src prepare_watershed_includes
python -m pytest -q
tools/smoke_wepp_binary_host.sh release/wepp_261010
tools/smoke_wepp_binary_host.sh release/wepp_261010_hill
python tools/run_hillslope_watchlist.py --binary release/wepp_261010_hill
python tools/check_ablation_artifact_policy.py
python release/wepp_261010_validation/compare_candidate.py
```

From WEPPpy:

```bash
tools/check_wepp_binary_provenance.sh wepp_runner/bin/wepp_261010 wepp_runner/bin/wepp_261010_hill
tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_261010
tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_261010_hill
tools/smoke_wepp_binary_in_container.sh wepp_runner/bin/wepp_261010
tools/smoke_wepp_binary_in_container.sh wepp_runner/bin/wepp_261010_hill
wctl run-pytest tests/wepp_runner tests/wepp/test_wepp_runner_outputs.py tests/wepp/interchange -q
wctl run-pytest tests/disturbed/test_matrix_contracts.py tests/disturbed/test_route_coefficients.py tests/weppcloud/routes/test_usersum_bp.py -q
```

The fresh matrix used the same release pair staged under
`/wc1/holdouts/wepp-261010-release-20261010`, selected through
WEPP_DISTURBED_BINARY, and the committed test_disturbed_matrix.py harness.
Its source/header history and fresh report identities are in the published
WEPPpy provenance sidecar. No old report is silently relabeled.
