# Native input capacity evaluation evidence

Status: evaluation complete. Evaluation only; no release, vendoring, deployment or
production Python-contract change.

## Source and scope

Native baseline: fetched default branch `wepp_260430_negmeltfix_comparator`,
commit `7d4cf4b5ab24bbc825515d54f25a035062b826bb`. Candidate commit is `fd7e0a5a6526ae217a58eb5bb2c491d75273610d`, adding
`src/input.for` reader-storage separation and evaluation tooling. Follow-up
commit `530ffb2be` adds the complete portable watershed evaluator; it does not
change the built native source. System `/usr/bin/gfortran` with pinned
`PATH=/usr/bin:/bin:$PATH`; standard make flags and sequential watershed/hill
builds. Both executables are retained under
`/workdir/native-soil-capacity-evidence/{baseline,candidate}/`.

The initial assessment inspected the dirty `kernelized-abandoned` checkout.
Its HBP state-shape warning does not describe the selected release line: the
actual baseline uses legacy ASCII pass-components version 3. The selected reader
also already consumes/discards surplus rows after clamping. The evaluation uses
only the fetched default-branch baseline and leaves shared checkout WIP intact.

## Observed data and bounded candidate

Read-only SQLite inventory on wepp1 found 359 components with horizon count
frequency: 1:8, 2:32, 3:65, 4:49, 5:42, 6:35, 7:44, 8:36, 9:23, 10:25.
Maximum distinct horizon count is ten. This is the run cache, not a national
SSURGO capacity survey. Evaluate eleven input horizons to cover its maximum plus
the mandatory 200 mm split; do not infer a universal production limit.

`mxhzin=11` sizes only input scratch arrays and local source depths. Calculation
`mxnsl=10`, grid construction, depth clipping, hydraulic equations, output layouts
and pass-file dimensions are unchanged. Unsupported counts stop explicitly.
The shared calculation-depth array no longer doubles as source input storage.

The real Zepol raw ten-horizon serialization is retained as `zepol_raw_10.sol`.
It was generated in a disposable process from the existing run-cache worker view,
with normal builder defaults. Boundary normalization was replaced with identity
only in that diagnostic process to capture text before the known rejection.
No production source or files were changed. Evaluation tooling inserts an exact
200 mm copy into its local artifact. This tests the soil with committed fixture
management/climate, not the original complete watershed workflow.

## Reader evidence

`tests/test_native_soil_input_capacity.py` compiles actual `input.for`, `profil.for`,
`eatcom.for`, `irinpt.for` and `rap_state.f90` with `-fcheck=all` and floating-point
traps. No reader or physical process is mocked. The driver supplies management
count zero and a simple slope, and reads back calculated depths, conductivity,
bulk density, field capacity, wilting point, texture, horizontal conductivity,
OFE counts and restrictive conductivity.

The new eleventh-material regression fails on the baseline: it creates six
calculation layers ending at 1.2 m instead of nine ending at 1.8 m, because the
last source horizon was discarded. Candidate passes that regression and the
count/format/multiple-OFE/deep-clipping matrix. Unsupported 0, 12 and 100 counts
fail with the explicit capacity diagnostic.

Eighty baseline/candidate probes (eight formats, counts 1–10, two OFEs each,
heterogeneous conductivity) match calculated state exactly. Detailed JSON:
`/workdir/native-soil-capacity-evidence/state-parity/report.json`.

## Complete hillslope execution

`tools/evaluate_soil_input_capacity.py` runs eight cases with baseline and candidate
hill binaries using the committed `delicate_game_pw0/p1` three-year inputs.
All sixteen executions complete the requested three years. All seven output
artifacts are byte-identical between builds for the original fixture and the
2-, 9-, and 10-horizon controls, including a low-conductivity runoff case. Candidate eleven-horizon synthetic outputs differ
from baseline as expected when the discarded horizon affects modeled depth.
Normalized Zepol produces byte-identical outputs between builds: its extra bottom
horizon is below the unchanged 1.8 m clamp, so Zepol alone cannot prove full input
consumption. The synthetic eleventh-material regression provides that proof.

An equivalent homogeneous two-versus-eleven-horizon comparison is not bitwise
invariant: four of seven artifacts differ, with maximum reported water-balance
field difference 0.02 and pass-field difference 0.046 (units depend on column).
The unchanged baseline two-versus-ten comparison has the same maxima. The baseline also exhibits subdivision sensitivity; this experiment does not
establish arbitrary new partitions as numerically equivalent.
The candidate matches old inputs exactly; do not claim arbitrary subdivisions
have identical transient results. Full comparator reports are retained.

Five timing samples per build for the original fixture show median elapsed
0.07 s and maximum peak RSS 4992 KiB for both builds using `/usr/bin/time`.
This small fixture shows no detected overhead, not a representative scaling claim.

## Additional coverage

The low-conductivity case produces 71 runoff-event records over three years.
The ten-horizon control is byte-identical between builds. Daily artifacts report
1800 mm throughout all 1095 records for candidate eleven-horizon input versus
1200 mm for the baseline.

The committed three-OFE `mofe_coefficient_ownership/default` case completes its
full sixteen-year period in both builds, both with original horizons and with
each OFE subdivided to eleven horizons. Original-input outputs are byte-identical.
The standalone reader also passes an independent overlap-weighted analytical
check of all nine calculated layers for heterogeneous eleven-horizon input.
There are 40 passing reader tests, including mixed OFE counts and materials
compared with isolated reads. Both binary smoke gates and all 31 permanent
hillslope watchlist cases pass.

## Broader validation and complete watershed execution

Full native pytest passes: 1785 passed, two preexisting tarfile deprecation
warnings, 632.86 seconds. The final targeted reader suite additionally covers
seven cases added after full-suite collection (40 targeted tests total).

The complete portable `physical_water` fixture passes two-year daily and hourly
runs for original single- and three-OFE inputs, and for eleven-horizon soils in
both the hillslope and channel input files. All twelve paired-build executions
finish both native stages; each build regenerates its own hillslope pass file.
All thirteen output artifacts match byte-for-byte for each original-input case.
The eleven-horizon case changes outputs as expected. Each channel water-balance
artifact has 731 finite daily rows, ending on day 365 of 1981. Native logs reach
simulation year two and report successful hillslope and watershed completion.
See `portable-watershed-comparison.json` for hashes and completion evidence.

The larger `delicate_game_pw0` replay regenerated 301 hillslopes per build:
2107 hillslope output files match byte-for-byte. Its watershed stage cannot
complete because the committed fixture lacks `pw0.str`, `pw0.chn` and `pw0.imp`,
as its README documents. Its replay helper returned success despite the native
missing-file message. The aggregate comparator found 2113 identical files,
including incomplete watershed artifacts; that is not watershed success evidence.
The portable fixture above supplies the complete watershed validation. A small
follow-up improvement is to make that existing replay helper verify native
completion markers before reporting success.

## Recommendation and promotion boundary

Proceed with a separate native input-capacity implementation rather than globally
increasing `mxnsl` or introducing horizon merging to address this incident. The
bounded eleven-horizon prototype retains original source properties and existing
calculation-grid semantics. Evidence supports this mechanism on the tested Linux
build and fixtures, not an arbitrary larger capacity or deeper modeled profile.

Before production adoption, decide and document the input capacity and explicit
excess-count rejection in an ADR and authoritative executable/soil contract.
If a limit above eleven is desired, inventory a broader SSURGO sample and rerun
capacity-boundary tests at the chosen limit. Retain ten calculation layers and
the existing 1800 mm depth treatment unless separately authorized.

WEPPpy must select/enforce the supported input count for the chosen executable;
never globally allow eleven while historical binaries silently truncate. Test
raw generation, prepared/Disturbed and multi-OFE serialization, channel soils,
and uploaded-input preservation with the actual selected binary. Keep the
200 mm normalization operation property-preserving and idempotent. Retain source
and generated-file provenance, including the native release identity.

The reported production job remains unfixed until those integration changes and
a paired binary release are authorized and validated. Do not deploy this task
branch or use its experimental binaries as a default. The next acceptance test
is an isolated full rebuild of `quasi-religious-allotment` through the real
WEPPcloud pipeline, with generated inputs read back and native outputs checked.
No production run, cache, config, binary or Python source was modified here.
