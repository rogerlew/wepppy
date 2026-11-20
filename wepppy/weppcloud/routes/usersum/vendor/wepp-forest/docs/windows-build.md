# Native Windows GNU Fortran build and mandatory parity gate

The latest validated native Windows pair is **wepp_261029 artifact revision 7**,
built from the unchanged accepted Linux revision-7 source; see the
[261029 validation record](windows-release-261029.md). The bootstrap default
remains **wepp_261027**. Build both executables from the same source commit.
WSL and IFX are not part of this lane. Earlier 261010/261026 Windows candidates
are not approved releases. The 261027 commands below remain a historical
reproduction example; use the exact source/tag and complete gates for each release.

## Toolchain and source

The validated host is blarhg, Windows 11 Home 10.0.26300, x86_64. Use native
WinLibs GNU Fortran/GCC **13.3.0 UCRT** and MSYS2 Bash, GNU make and tar. The
validated compiler directory is `C:\tmp\winlibs-gcc133\mingw64\bin`; MSYS2 Bash
is `C:\msys64\usr\bin\bash.exe`. Use native Windows Python 3.11 or newer for
the replay helpers. MSYS2 supplies build utilities; the resulting executables
run directly on Windows without MSYS2, WSL or separately installed GNU DLLs.

Verify `git symbolic-ref refs/remotes/origin/HEAD` and the checked-out branch.
The canonical branch is `wepp_260430_negmeltfix_comparator`. Build from a clean
committed-source snapshot, not a dirty working directory. The exact source for
261027 is `3e55e01b3768f71be30e40e57431d8fb6afd116e`; the later canonical branch
also contains the release validation helpers and committed fixtures.

## Build the matched pair

Run the following in MSYS2 Bash from a canonical repository checkout. Choose a
new build directory each time; this example refuses to reuse an existing one.
For a future release, replace the source commit and output tag together and
perform all gates below. Do not overwrite an already published dated release.

```bash
set -euo pipefail
base=/c/tmp/wepp-native-261027-rebuild
mkdir "$base"
mkdir "$base/source" "$base/release"
source_commit=3e55e01b3768f71be30e40e57431d8fb6afd116e
git archive "$source_commit" src fpm-src > "$base/source.tar"
tar -xf "$base/source.tar" -C "$base/source"
export PATH=/c/tmp/winlibs-gcc133/mingw64/bin:/usr/bin:$PATH
fc=/c/tmp/winlibs-gcc133/mingw64/bin/gfortran
"$fc" --version
gcc --version
cd "$base/source/src"
make clean
make -B -j4 FC="$fc" LINKER="$fc" \
  LDFLAGS='-mcmodel=medium -static' \
  WATERSHED_INCLUDE_DIR=includes_windows wepp \
  > "$base/build-watershed.log" 2>&1
cp wepp.exe "$base/release/wepp_261027.exe"
make -B -j4 FC="$fc" LINKER="$fc" \
  LDFLAGS='-mcmodel=medium -static' wepp_hill \
  > "$base/build-hill.log" 2>&1
cp wepp_hill.exe "$base/release/wepp_261027_hill.exe"
sha256sum "$base/release/"*.exe
objdump -p "$base/release/wepp_261027.exe" | grep 'DLL Name'
objdump -p "$base/release/wepp_261027_hill.exe" | grep 'DLL Name'
size "$base/release/"*.exe
```

Build the watershed and hillslope targets sequentially: the makefile switches
include profiles. Preserve the makefile's shared math runtime, linker wrappers
and compiler controls; do not substitute an unrelated compiler or math library
and assume parity. The paired C compiler is resolved alongside the pinned FC.

The Windows watershed uses all four capacity includes in `src/includes_windows`:
4,500 hillslopes, 1,500 channels and 6,000 elements. The hill profile supports
32 OFEs. Linux retains 45,000 hillslopes, 15,000 channels and 60,000 elements.
Windows static BSS is approximately 183 MiB for the watershed and 2.3 MiB for the
hill executable, excluding runtime memory. Keep capacity includes synchronized.

## Mandatory release acceptance

**Do not publish, vendor, register as selectable, or promote a Windows build
until every gate below passes for the actual final binaries.** Successful
compilation, completion banners, function probes or a small smoke test alone do
not establish release parity. Re-run the gates after any binary rebuild or
source, compiler, flags, math-runtime or capacity change.

1. Run the canonical Linux release gates from AGENTS.md: both host smokes,
   hillslope watchlist, full pytest suite with the pinned system compiler,
   ablation artifact policy, and ELF interpreter compatibility. Pin the
   accepted Linux baseline explicitly; do not silently replace it to pass parity.
2. Run the complete release suite natively on Windows and Linux with identical
   committed inputs and matched binaries from the same source revision. The
   261027 suite contains 22 hillslope cases and 10 paired watershed controls
   (32 executions per platform), including the long-period watchlist cases.
3. Run a medium full watershed on both platforms. The required current fixture
   is `tests/fixtures/redoubled_catmint_watershed/runs.tar.gz`: **491 hillslopes,
   211 channels, all nine configured years (2016–2024)**. Independently regenerate
   every hillslope and then run the watershed using that platform's fresh PASS
   files. Do not copy PASS files between platforms or truncate the simulation.
4. Require successful process exits and model success markers, complete daily
   calendars, finite outputs and valid source metadata. Run
   `tools/validate_late_return_watershed.py` on each medium replay. This check
   supplements parity; it does not prove independent water conservation.
5. Inventory **every output file** using `tools/native_output_inventory.py`.
   Require identical relative file sets and identical `lf_sha256` for every
   file. The only allowed normalization is CRLF to LF. No file exclusions,
   numerical rounding, stale-output reuse or relaxed tolerances are permitted.
   Check input manifests too. For the accepted 261027 release, this is 214/214
   small-suite files and 3,443/3,443 medium-run files.
6. Retain commands, source/compiler identities, binary hashes, execution
   receipts, input/output inventories and comparison results in the source
   repository. Diagnose any failure under the ablation protocol and leave the
   candidate unvendored. A changed numerical baseline needs explicit approval
   and a new release identity; it is not an automatic exception to this gate.

For the small suite, use the recorded case definitions and execution evidence in
[the release validation](ablation/20261027-native-portability/release-validation.md)
and [the Windows validation](ablation/20261027-native-portability/windows-release-validation.md).
The initial staging and native runner are retained in the bootstrap
[parity package](https://github.com/rogerlew/wepppy-win-bootstrap/tree/master/docs/work-packages/20261027_native_windows_parity)
and `tools/run_windows_release_cases.py` in that repository. Pin the bootstrap
commit when using these cross-repository helpers; the completed release package
is recorded at bootstrap commit `4a6a2f4`.

From the canonical source checkout, a native Windows medium replay can be run
in PowerShell (substitute your checkout, Python and binary paths):

```powershell
python tools/replay_native_watershed.py --archive tests/fixtures/redoubled_catmint_watershed/runs.tar.gz --destination C:/tmp/medium-261027-fresh --hill C:/tmp/wepp-native-261027-rebuild/release/wepp_261027_hill.exe --watershed C:/tmp/wepp-native-261027-rebuild/release/wepp_261027.exe --workers 4
python tools/validate_late_return_watershed.py --root C:/tmp/medium-261027-fresh --result C:/tmp/medium-261027-validation.json
python tools/native_output_inventory.py --root C:/tmp/medium-261027-fresh --result C:/tmp/medium-261027-inventory.json
```

Check each command's exit code before continuing. Repeat on Linux with a fresh
destination and the accepted Linux binary pair. `--root` is the replay root,
not its `output` subdirectory. The replay isolates hill working directories and
requires a previously nonexistent destination. Allow several GB of disk space
per platform. Reduce `--workers` for limited memory without reducing case scope.

Compare the two inventory JSON objects with this exact gate:

```python
import json
from pathlib import Path

linux = json.loads(Path('linux-inventory.json').read_text())
windows = json.loads(Path('windows-inventory.json').read_text())
assert linux and linux.keys() == windows.keys(), 'Output file sets differ'
different = [name for name in linux
             if linux[name]['lf_sha256'] != windows[name]['lf_sha256']]
assert not different, different
```

Apply the same gate to the small suite's per-case inventories; verify identical
input manifests before interpreting output comparisons.

## Packaging and handoff

Keep versioned watershed/hillslope binaries together with JSON sidecars recording
source branch/commit, compiler, capacities, SHA-256 and completed validation.
Inspect both PE import lists: the accepted build imports only Windows system and
UCRT DLLs. Linux ELF interpreter checks do not apply to native PE executables.
A rebuild may have different binary bytes because of build metadata; it still
requires new hashes and the full output-parity gate.

The bootstrap's `--wepp_exec wepp_261027` selects an indivisible registered pair
for Windows or Linux. Both artifact checksums are pinned in its release registry;
independent hill overrides and arbitrary executable paths are unsupported.
The Windows `wepppy-win-bootstrap.exe` compatibility alias must equal the
watershed binary. Regenerate all hillslope PASS files before watershed execution.

Record the release in `change-log.md`, update release notes and sidecars, commit
and push the source evidence, then vendor the exact validated pair and run the
native bootstrap command through CSV export. See the
[261027 validation record](ablation/20261027-native-portability/windows-release-validation.md)
for accepted hashes, retained evidence, timings and the limits of the parity claim.
