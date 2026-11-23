# Native Windows WEPP 261029 build and bootstrap handoff

## Purpose and scope

Build the existing revision-7 algorithm unchanged on native Windows blarhg and
vendor a validated matched pair into `/workdir/wepppy-win-bootstrap`. User requests
a quick parity check as well. This is an exact-source platform build, not model
modernization or permission to change the accepted Linux numerical baseline.
Model source: e0abe0581f77c6f66917e90daf8f8f429e9315c8, canonical branch
wepp_260430_negmeltfix_comparator. Linux watershed SHA256 4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825;
hill SHA256 210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936.

## Plan and acceptance

1. Build from git archive on blarhg using WinLibs GNU 13.3 UCRT in
   C:/tmp/winlibs-gcc133/mingw64/bin and MSYS2 Bash. Sequential watershed/hill
   targets, static linking, all four includes_windows watershed capacity files.
   Isolated build root: C:/tmp/wepp-261029-windows-20261105.
2. Quick check first: identical committed physical-water daily/hourly controls
   plus the complete current watchlist, fresh outputs on both platforms. Stage
   using the committed physical_water_case helper and watchlist run directories.
   Cross-repo runner pinned to bootstrap 3fd30d0. Record every input hash.
3. Per docs/windows-build.md, full native Linux gates and full medium fixture
   parity precede vendoring. Independently regenerate 491 hillslopes and route
   211 channels across all nine years 2016–2024 using the committed archive.
   Use replay_native_watershed.py, validate_late_return_watershed.py and
   native_output_inventory.py. File sets and every LF-normalized output hash
   must agree; only CRLF normalization allowed. Keep all failed evidence.
4. If a gate fails, keep candidate unvendored, investigate under the ablation
   protocol, and do not silently relax tolerance or replace the Linux baseline.
5. On acceptance, add versioned Windows pair and sidecars, register checksums
   for explicit --wepp_exec wepp_261029 selection, preserve the existing default
   and compatibility alias absent an explicit default-switch request. Exercise
   native bootstrap through CSV export and run packaging tests. Record hashes,
   commands and results in both repositories and the native changelog.

## Progress

- [x] Read source and bootstrap Windows build/release contracts; SSH works.
- [x] Verify source branch and exact accepted Linux identities.
- [x] Start native Windows archive build in a fresh directory.
- [x] Quick parity: 20 executions and 130/130 output files match after CRLF normalization.
- [x] Expanded parity: 51 executions and 347/347 files match; all Linux gates pass (1752 tests).
- [x] Medium parity: 3443/3443 files and 2468 input hashes match; both semantic validators pass.
- [x] Matched sidecars and explicit bootstrap selection vendored; native 1461-row CSV/calendar/finite check and packaging tests pass.

## Discoveries and decisions

- Native `python` on PATH is an inactive Store alias; use
  C:/Users/roger/miniconda3/python.exe (Python 3.12.9).
- Existing source and bootstrap unrelated/untracked files remain untouched.
- A quick check is an early result, not a waiver of mandatory vendoring gates.

## Outcomes

All gates pass. Quick 130/130, expanded 347/347, medium 3443/3443 output
parity; 2468 medium inputs identical. Linux 1752 native tests pass. Windows
bootstrap consumes the vendored pair through 1461 finite daily CSV rows; both
platform packaging suites run 21 tests; Linux skips two Windows-only cases,
Windows passes all 21.
Source release evidence committed/pushed as fb5c4af03; bootstrap handoff
committed as 7922280. Existing defaults and alias unchanged.

## Handoff validation observations

The first bootstrap staging attempt correctly rejected input files copied from
a previously executed case because the model had changed those files. The
accepted run instead extracted the original checksum-bound input archive into
a fresh project. A first CSV reader attempt omitted the established four-line
title/area preamble; reading with skiprows=4 verified the generated artifact.
Neither issue was a native model failure or a change to accepted inputs/outputs.
