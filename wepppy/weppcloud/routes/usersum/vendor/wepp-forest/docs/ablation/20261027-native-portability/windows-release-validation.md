# Native Windows wepp_261027 release validation

Validated on 2026-10-27. Only 261027 is released for native Windows; the earlier
261010/261026 investigation and proposed backport are superseded by this scope.
No WSL or IFX is used. Historical Linux artifacts remain unchanged.

## Provenance and build

Canonical source branch: `wepp_260430_negmeltfix_comparator`.
Build source: `3e55e01b3768f71be30e40e57431d8fb6afd116e`.
Native host: blarhg, Windows 11 Home 10.0.26300, x86_64.
Compiler: WinLibs GNU Fortran/GCC 13.3.0 UCRT. Build from a clean git archive:

```bash
make clean
make -B -j4 FC=/c/tmp/winlibs-gcc133/mingw64/bin/gfortran LINKER=/c/tmp/winlibs-gcc133/mingw64/bin/gfortran LDFLAGS='-mcmodel=medium -static' WATERSHED_INCLUDE_DIR=includes_windows wepp
make -B -j4 FC=/c/tmp/winlibs-gcc133/mingw64/bin/gfortran LINKER=/c/tmp/winlibs-gcc133/mingw64/bin/gfortran LDFLAGS='-mcmodel=medium -static' wepp_hill
```

The watershed profile supports 4,500 hillslopes, 1,500 channels and 6,000 elements;
the hillslope profile supports 32 OFEs. Static BSS is 191,626,304 and 2,425,728
bytes respectively. System Windows/UCRT DLLs supply runtime services; no separate
GNU runtime DLL is required. JSON sidecars identify exact binary hashes:

| Binary | SHA-256 |
| --- | --- |
| wepp_261027.exe | ad4a14e56ff5da4670c8c40dbfbd187299d6ee54e9b0a76ddf6df3cde4ab880f |
| wepp_261027_hill.exe | 50e650645b4784aca9175c55aa9b508d8b2214b597409b466b2c084dd9408f0b |

## Parity acceptance

The new Linux 261027 baseline passed 537 regression tests, both host smokes,
12 hillslope watchlist cases and the 32-execution release suite. This Windows
release repeats all 32 executions: 22 hillslope cases and 10 paired watersheds.
All 214 output files match Linux after CRLF-to-LF normalization only.

The committed source fixture `tests/fixtures/redoubled_catmint_watershed/runs.tar.gz`
has SHA-256 `570fb6a30874f1ee15e8ce6a1459befd18181d3960a54da527e82fa43d9c274e`.
Both hosts used the same 2,468 input files. Each independently regenerated all
491 hillslopes in isolated directories and then routed the full 211-channel
watershed for all nine configured years, 2016–2024. No cross-platform PASS reuse.
Four hillslope processes ran concurrently. Every execution succeeded.

All **3,443 output files** match exactly after CRLF-to-LF normalization. No files,
columns, numerical differences or whitespace other than CRLF were excluded.
The validators also agree exactly: 3,288 daily records per hill, 693,768 channel
rows, finite channel values, zero negative channel values, two active SRC3
return-source records, and the complete outlet calendar through 2024-12-31.
Linux elapsed 230.77 seconds; Windows 596.67 seconds, including watershed times
103.28 and 356.13 seconds. These timings are observations, not benchmarks.

## Reproduction and evidence

In the canonical wepp-forest checkout, use a fresh destination for each host:

```bash
python tools/replay_native_watershed.py --archive tests/fixtures/redoubled_catmint_watershed/runs.tar.gz --destination /tmp/medium-fresh --hill /path/to/wepp_261027_hill --watershed /path/to/wepp_261027 --workers 4
python tools/native_output_inventory.py --root /tmp/medium-fresh --result /tmp/medium-inventory.json
```

Use the corresponding `.exe` paths on native Windows. Compare complete inventory
path sets and every `lf_sha256`; the raw hashes are retained too. Source evidence
is under `docs/ablation/20261027-native-portability/artifacts/windows-261027/`:
input/output manifests, execution receipts, semantic validation results,
comparison summaries and compressed build logs. Full raw outputs remain in the
temporary run directories because each platform generated approximately 2.1 GB.

## Bootstrap integration and limits

The bootstrap selects the matched versioned hill/watershed pair. Its fixed
`wepppy-win-bootstrap.exe` alias equals the watershed binary. The PASS reader now
recognizes version 3 and rejects unknown versions; daily totals still use the
legacy daily records, not the added SRC3 metadata. The actual native bootstrap
command completed a four-year paired case through `totalwatsed2.csv` export with
`--numcpu 1`. This option now controls the hillslope process pool.

This establishes parity for these fixtures and pinned compilers, not a universal
cross-platform floating-point guarantee or independent water-conservation proof.
The nine-year run exercises medium capacity, not the compiled maximum. Existing
shared-directory bootstrap scratch-file risks remain; the extensive model replay
uses isolated hillslope directories. Production deployment was not performed.

Packaging verification: bootstrap unittest suite passed 14 tests on Linux (two
Windows-only downloader checks skipped); the two new packaging/PASS tests also
passed natively on Windows. The output-inventory chunk-boundary regression test
passed. Documentation lint reported zero errors or warnings. Model source is
unchanged since the previously completed 537-test Linux release gate.
