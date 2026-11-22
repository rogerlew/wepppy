# wepp_261027 Linux release validation

Status: passed. Roger authorized the shared math runtime as a new Linux baseline
on 2026-10-27 and selected release name `wepp_261027`. Both release executables
and their JSON sidecars are retained under `release/`.

## Identities

The verified remote-default branch is `wepp_260430_negmeltfix_comparator`.
Build source commit: `3e55e01b3768f71be30e40e57431d8fb6afd116e`.
Validation commit: `e90d2ae00660dd1a216046f89903a0a80fc10e42`.
Only test/evidence handling changed between these commits; source, fpm-src and
build-script trees are identical. Sidecars retain the actual build identity
and record the validation commit separately.

| Artifact | SHA-256 |
| --- | --- |
| wepp_261027 | ed309dd19e4b44f88b6aa9df4d2a883aa6ea5dd3baeeb8b30fc142886665f27b |
| wepp_261027_hill | 6be5ce1fc8bc9cad71f1d5d849a13d90baa3b8df821416e917ad94e611750e5a |

GNU Fortran and GCC are Ubuntu 13.3.0-6ubuntu2~24.04.1. Both ELF interpreters are
`/lib64/ld-linux-x86-64.so.2`. Linux retains its 45,000-hillslope/15,000-channel/
60,000-element watershed capacity and 32-OFE hillslope capacity. The banner,
Gregorian calendar and PASS component-v3 interchange remain unchanged.

## Completed gates

- Full pytest: 537 passed, 2 warnings in 565.76s.
- Host smoke: both dated executables passed.
- Canonical permanent hillslope watchlist: 12 passed, zero failures.
- Fresh model replay: 32 successful executions across 22 hillslopes and ten
  paired four-year physical watershed controls. Complete configured periods were
  used; the watchlist includes 45-year and 100-year hillslopes. This is not a
  claim of fresh 100-year watershed durability testing with the new binary.
- Accepted-candidate comparison: all-output, water and erosion gates pass in all
  22 cases. Every one of the 214 output files is byte-identical to the checked
  accepted Linux candidate. No tolerance, structural check or exclusion changed.
- Integrated math probe: all 145,937 evaluations exactly match the accepted
  candidate probe, which was bit-identical across Linux and native Windows.
- Independent rebuild from the committed source archive: both normalized ELF
  images are identical after removing debug information and GNU build IDs only.
- Ablation artifact policy, documentation lint and recorded SHA-256 checks passed.

## Regression adjustment

The first full pytest invocation produced 536 passes and one failure. The
late-return writer locality test compared the current executable with 261021
and required every file except its single SRC3 record to remain byte-identical.
That mixed the authorized new math policy with the writer-only comparison.

The revised test builds the current source with only the late SRC3 writer branch
turned off. It still requires all other output files and every other pass record
to match exactly. It also requires the paired control to reproduce the invalid
late-return event. Historical 261021 characterization tests remain unchanged.
The focused seven-test suite and the subsequent complete suite pass. Neither
production source nor release executable changed to resolve this test failure.

## Reproduction and evidence

From the canonical worktree, with `/usr/bin` first in PATH:

```bash
TARGET_TAG=261027 tools/build_wepp_dated_release.sh
tools/smoke_wepp_binary_host.sh release/wepp_261027
tools/smoke_wepp_binary_host.sh release/wepp_261027_hill
python tools/run_hillslope_watchlist.py --binary release/wepp_261027_hill
pytest -q
python tools/check_ablation_artifact_policy.py
```

`artifacts/release-261027/` retains build logs, both pytest outcomes, writer
regression results, smoke/watchlist logs, 32 execution receipts, comparisons,
clean-build equivalence and metadata-finalization commands. Inputs remain the
committed watchlist resources and the deterministic controls from committed
source `d354e3c998f81955f9d9e5ca7d01ca56e1a9f04b`. Full generated replay outputs are
under `/tmp/wepp-release-261027/cases`; they are reproducible temporary data.

## Handoff boundary

The new Linux behavior is intentional; historical differences remain recorded in
[campaign-continuation.md](campaign-continuation.md). Use the matched 261027 pair
and regenerate contributing hillslope and watershed outputs. Historical releases
are untouched. The inherited dry-day SRC3 timing approximation and routing
limitations remain documented in the release notes and sidecars.

Linux release validation is complete. Downstream vendoring, native Windows
release packaging, project-default selection and deployment were not performed.
