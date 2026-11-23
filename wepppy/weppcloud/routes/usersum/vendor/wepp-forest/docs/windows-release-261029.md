# Native Windows WEPP 261029 revision 7

Validated November 5, 2026 on native Windows host `blarhg`. This is a platform
build of the existing Linux revision-7 source, not a new numerical baseline.
The approved consolidated report remains unchanged; its preparation-time
statement that no Windows release was included predates this separate release.

## Identity and compatibility

Source branch: `wepp_260430_negmeltfix_comparator`. Exact model source:
`e0abe0581f77c6f66917e90daf8f8f429e9315c8`. A clean `git archive` of `src` and
`fpm-src` supplied the build. Native compiler: WinLibs GNU Fortran/GCC 13.3.0 UCRT;
MSYS2 Bash supplies build utilities, not the runtime. No WSL or IFX was used.

| Binary | SHA256 |
| --- | --- |
| `wepp_261029.exe` | `9d7b34295e7fda97de9804b142d11604c404c548f9987e30f59af273f4747107` |
| `wepp_261029_hill.exe` | `a1476ca5be83be3af429124426bee14511b4f1e8e93d17868395c50bad131d97` |

The Windows watershed profile uses all four `includes_windows` capacity files:
4,500 hillslopes, 1,500 channels and 6,000 elements. The hillslope profile supports
32 OFEs. Static BSS is 191,807,392 bytes for watershed and 2,430,528 for hill.
Both executables import only Windows system/UCRT DLLs; no separately installed
GNU runtime is required. JSON sidecars identify artifact revision 7 and Windows
platform-artifact revision 1. The `2020.500` banner and model source are unchanged.

## Build commands

From the archived source in native MSYS2 Bash, pin the compiler directory first
on PATH and build watershed and hill sequentially:

```bash
export PATH=/c/tmp/winlibs-gcc133/mingw64/bin:/usr/bin:$PATH
fc=/c/tmp/winlibs-gcc133/mingw64/bin/gfortran
make clean
make -B -j4 FC="$fc" LINKER="$fc" LDFLAGS='-mcmodel=medium -static' WATERSHED_INCLUDE_DIR=includes_windows wepp
make -B -j4 FC="$fc" LINKER="$fc" LDFLAGS='-mcmodel=medium -static' wepp_hill
```

The complete [build script](work-packages/20261105_windows_261029/artifacts/build.sh)
and compressed build/PE-inspection logs are retained with the evidence. The
paired C compiler resolves beside the pinned Fortran compiler. No numerical
compiler flags, math wrappers or model source were changed to obtain parity.

## Generated-output parity

The fixed Linux reference pair has watershed SHA256
`4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825` and hill SHA256
`210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936`.
Its original binaries and sidecars were not modified.

| Gate | Result |
| --- | --- |
| Quick check: five layouts, daily/hourly, four years, paired hill/watershed | 20 executions/platform; 130/130 output files identical |
| Complete current release suite: quick controls plus 31 watchlist hillslopes | 51 executions/platform; 347/347 output files identical |
| Small-suite inputs | All 571 staged file hashes match |
| Medium watershed: independently regenerated 491 hillslopes, 211 channels, full 2016–2024 | 3,443/3,443 output files identical |
| Medium inputs | All 2,468 file hashes match |
| Medium semantic validation | Identical complete calendars, finite channel values, valid active SRC3 metadata and outlet end date 2024-12-31 |
| Linux release gates | Both smokes, 31/31 watchlist, artifact policy, system ELF interpreter and 1,752 pytest tests pass |
| Windows PE imports | Windows system/UCRT only |

Every output file is inventoried. Only CRLF-to-LF normalization is allowed;
there are no numerical tolerances, column/file exclusions or reused PASS files.
Each platform regenerates its own hill/PASS/watershed chain in fresh directories.
The quick check is a subset of the complete suite, not an additional 130 files.

The committed medium fixture is
`tests/fixtures/redoubled_catmint_watershed/runs.tar.gz`, SHA256
`570fb6a30874f1ee15e8ce6a1459befd18181d3960a54da527e82fa43d9c274e`.
Use `tools/replay_native_watershed.py`, `tools/validate_late_return_watershed.py`
and `tools/native_output_inventory.py` as documented in [Windows build instructions](windows-build.md).
The small-suite runner is pinned to bootstrap commit
`3fd30d070577f22a4c3e490903af1a9e5e60628b`; the staging recipe and exact inputs are
recorded in the [execution package](work-packages/20261105_windows_261029/prompts/completed/build_execplan.md).

## Interpretation and delivery

This establishes exact output parity for these fixtures and compilers, not
universal floating-point equivalence, maximum-capacity testing, field calibration
or independent whole-watershed conservation. Specialized RAP full-history
cross-platform parity is not claimed by this campaign. The existing scientific
limitations of revision 7 remain in force.

The Windows pair is vendored in `/workdir/wepppy-win-bootstrap` as an explicit
`--wepp_exec wepp_261029` selection. The current `wepp_261027` default,
`wepppy-win-bootstrap.exe` compatibility alias and legacy `--revegetation`
selection remain unchanged. Native bootstrap execution with explicit selection completes a fresh four-year
case and exports 1,461 daily rows with a complete 1980–1983 calendar and finite
values. Packaging suites pass on Linux and Windows (21 tests each, two
Windows-only skips on Linux; no Windows skips). The [receipt](work-packages/20261105_windows_261029/artifacts/bootstrap-receipt.json)
and compressed logs retain actual consumption evidence. No production deployment
is included.
