# Native math-runtime campaign continuation

Date: 2026-10-27. Status: experimental candidate; release promotion remains open.

The remaining p40 divergence is reproducible through platform math-library
results. A shared dispatch experiment eliminates every numeric water difference
over its full 100-year record. It uses native Windows gfortran on blarhg, without
WSL or IFX. This is paired-candidate parity, not reproduction of unchanged
historical Linux releases.

## Observation before changes

GNU linker wrappers record the arguments, results and caller addresses of native
math functions without changing their return values. The first 30 days of the
unchanged 100-year p40 input are exploratory; an intentional exit 97 ends tracing.
Both completed traces reproduce all 240 printed first-month water records from
their respective uninstrumented baselines exactly. An earlier incomplete Windows
trace was discarded and repeated with a longer timeout.

Matching argument/date/OFE/function keys found 121 differing result contexts:
30 asin, 76 acos, 10 power, three logarithm and two exponential results. These are
different matched keys, not a count of every call. Windows runtime internals also
call double functions, so raw log lengths are not expected to match. Linux caller
addresses map the differences to aspect, sunmap, watbal_hourly, perc, dblex and
runge. The retained analysis identifies individual source lines and bit patterns.

## Controlled experiments

Every row below uses fresh outputs, the full configured 100-year p40 record and
bounds-checked gfortran 13.3 builds on both platforms. Each narrower lane starts
from the previously corrected candidate; combined lanes are labeled explicitly.
No change was promoted into production source during this continuation.

| Experiment | Largest daily QOFE difference, mm | Disposition |
| --- | ---: | --- |
| Corrected candidate baseline | 116.18182 | Remaining failure |
| perc power evaluated in double, rounded to real | 116.18182 | No improvement; rejected |
| Scalar logarithms evaluated in double | 116.18182 | No improvement; rejected |
| watbal_hourly day-length acos evaluated in double | 116.18182 | No improvement; rejected |
| asin calls evaluated in double | 116.18182 | No improvement alone |
| Only the two sunmap acos calls evaluated in double | 0.48011 | Isolates the dominant contribution |
| All asin/acos calls evaluated in double | 0.48004 | Erosion passes; water still fails |
| Previous row plus shared sine/cosine dispatch | 0.304949 | Smaller residual; water still fails |
| Shared float math-runtime dispatch | 0 | Water and erosion pass |

The final lane uses the existing deterministic sine/cosine kernel, and evaluates
asin, acos, atan, tan, exp, log, log10 and power in double before one real32
conversion. Four-wide GNU vector sine, cosine, logarithm and power calls receive
the same scalar policy. Original double-precision model calls remain unchanged.
The glue is retained as `artifacts/campaign/runtime-wrap.c`; it is an experimental
GNU linker mechanism, not a claim of a portable ABI on every compiler or CPU.

The sunmap lane establishes the dominant contribution, but does not explain every
remaining difference individually. The broader runtime experiment closes the
observed p40 residual without a model threshold, epsilon or output exclusion.
The earliest printed difference at year 1/day 28 disappears in that lane.

## Function and model validation

- 145,937 actual-trace and seeded probe evaluations: zero cross-platform result
  bit differences. Each replacement differs from either host's native float
  function by at most one float32 ULP on these samples. This is sampled evidence,
  not a proof over every floating-point argument.
- Sine/cosine maximum absolute difference in this probe is 5.96e-8. The earlier
  151,109-angle test over the specified range remains the wider 1e-4 contract gate.
- All 22 hillslope cases completed on each platform with bounds checks enabled.
  All 22 pass all-output 1%, water 1% and erosion 10% comparisons, with absolute
  floor 1e-9 and structural checks. No file exclusions or thresholds were relaxed.
- All ten paired physical hillslope/watershed controls completed and passed the
  all-output 1%, water 1% and erosion 10% comparisons, with absolute floor 1e-9.
  These are complete four-year controls, not 100-year watershed durability tests.
- p40 has 292,192 water records and zero numeric differences over 100 years.
  Water and erosion file comparisons pass without loosening their thresholds.
- Linux watershed/hillslope interpreters are `/lib64/ld-linux-x86-64.so.2`.
  Windows imports only system/UCRT DLLs. The Windows watershed uses the authorized
  4500-hillslope/1500-channel capacity; BSS is 191,629,856 bytes. BSS is not peak RAM.

## Historical-reference boundary

Comparing the new Linux candidate with the prior corrected Linux candidate gives
12/22 water passes and 20/22 erosion passes. All ten physical controls pass those
two gates, but the long watchlist differences remain material. Matching platforms
does not make those differences scientifically neutral. In p40, even one-ULP
function changes can alter daily runoff timing decades later.

The runtime lane therefore has `requires_scientific_review` disposition for
promotion. It demonstrates a native cross-platform route, while retaining the
previous Linux behavior as a separate reference. It does not establish parity
with unchanged wepp_261010 or wepp_261026 release artifacts, and no such artifacts
were overwritten or vendored. The 261010 backport has not been performed.

The previous 536-test result applies to the earlier source repair step. Full
release pytest/watchlist and downstream vendoring gates have not been claimed
for this isolated runtime experiment. Production integration, matched release
provenance, historical-version backports and those gates remain release work.

## Retained evidence and reproduction

`artifacts/campaign/` retains all lane builders/runners, C wrappers, math probes,
compressed trace/probe inputs and outputs, comparison JSON, execution receipts,
build logs and hashes. The source is the prior corrected archive on default
branch `wepp_260430_negmeltfix_comparator`, parent `8d89b0c19`; provenance records
its exact archive hash. The committed fixture source remains
`d354e3c998f81955f9d9e5ca7d01ca56e1a9f04b`.

The lane builders reuse `/tmp/native-portability-fix-20261027/checked` (or its
native Windows counterpart), built by the previously retained builder from the
recorded corrected source archive. Run `build-runtime.sh linux` or
`build-runtime.sh windows` under MSYS on blarhg; the latter pins WinLibs 13.3 UCRT.
Then run `stage-runtime-full.py` and `run_windows_release_cases.py` with the new
candidate_hill path. `build-runtime-watershed.sh` and
`stage-runtime-paired.py` reproduce the paired controls. The comparison scripts
use the committed raw comparator, not a custom relaxed gate.

Complete model outputs remain in `/tmp/native-parity-campaign-20261027` and
`C:/tmp/native-parity-campaign-20261027`. These temporary trees are not durable
archives. Retained compressed traces can be decompressed into the analysis
script's expected working directory; function-probe inputs are retained exactly.
