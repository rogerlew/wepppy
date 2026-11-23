# 2026-04-14 Numerical Stability Patches: Active Set, Rolled-Back Set, and Ablation Results

## Scope
This file documents exactly what was changed in `src/` during the 2026-04-14 watershed-stall incident response, what was rolled back, and what is currently active.

The intent is conservative rollout: fix the observed stability failures with the smallest defensible patch set.

---

## Current Active `src` Changes (Minimal Set)

### A) `src/newton.for` (active)
What changed:
- Replaced the legacy open-ended Newton update loop with a bounded bracket + bisection flow.
- Added guards for degenerate inputs (`avesm <= 0`, `time <= 0`, `aveks <= 0`).
- Added bounded bracket expansion and bounded bisection iterations.
- Clamped final `ffnow` to non-negative.

Why:
- The original loop could fail to converge and spin indefinitely, causing watershed runs to appear hung.

Why this improves stability:
- Guaranteed termination in bounded iterations.
- Removes non-convergent infinite-loop behavior.

Computational regression risk:
- Medium.
- Numeric trajectory differs from historical Newton step path, especially near difficult conditions.

Correctness vs original:
- More correct operationally (termination + no undefined loop behavior).
- Not bitwise-equivalent to legacy trajectories.

---

### B) `src/mann.for` (active)
What changed:
- Explicit initialization of saved state:
  - `ichanx = -999999`
  - `q0x = -1.0e30`
  - `yx = 0.0`

Why:
- Remove compiler/runtime dependence on implicit initial values for `SAVE`d locals.

Why this improves stability:
- Deterministic first-call behavior across compilers/builds.

Computational regression risk:
- Low.

Correctness vs original:
- More correct and deterministic.

---

### C) `src/infile.for` (active)
What changed:
- Replaced `partcf = cuthgt/hmax` blind division with explicit assertion:
  - If `hmax > 0`, compute as before.
  - If `hmax <= 0`, print explicit error (`6050`) and `stop` immediately.

Why:
- `hmax=0` produced FP traps/divide-by-zero behavior under current compiler flags.
- Silent coercion was intentionally avoided per request; this is explicit fail-fast.

Why this improves stability:
- Deterministic failure contract instead of late/opaque FP traps.

Computational regression risk:
- Behavioral strictness increase: previously some builds may continue with undefined/implicit handling.
- This now fails invalid inputs immediately by design.

Correctness vs original:
- More correct from input-contract perspective (invalid plant parameter should not proceed).

---

### D) `src/wepp_observe.for` + channel call-site hooks (active)
What changed:
- Added new opt-in logger subroutine:
  - `src/wepp_observe.for`
  - Writes one line per marker to `wepp_observe.log` when `wepp_observe.on` exists.
- Added call-site markers in:
  - `src/wshdrv.for`: `CHNERO_BEGIN`, `CHNERO_END`
  - `src/chnero.for`: `CHNRT_BEGIN`, `CHNRT_END`
  - `src/chnrt.for`: `CHNRT_ENTER`, `CHNRT_SEG`, `CASE12_BEGIN/END`, `CASE34_BEGIN/END`, `CHNRT_EXIT`
- Wired into build lists in `src/makefile` (`wepp_observe.o`, `wepp_observe_hill.o`).

Why:
- We were blind during stall/fpe triage: `wepp_observe.on` existed operationally, but there was no durable phase log in the active code path.

Why this improves stability operations:
- No model-behavior change; this is observability only.
- Converts opaque “running forever” or “SIGFPE somewhere in routing” into exact last-executed phase/segment evidence.

Computational regression risk:
- Very low when `wepp_observe.on` is absent (no-op).
- Debug runs with `wepp_observe.on` incur I/O overhead by design.

Correctness vs original:
- Numerically equivalent intent in normal mode (flag off).
- Strictly better diagnosability in observe mode.

---

## Rolled-Back Experimental Changes (Not Active)
The following edits were made during triage and then rolled back to minimize regression risk:

1. `src/wshdrv.for` dry/no-storage short-circuit before `wshchr` with explicit state zeroing.
2. `src/wshchr.for` multiple early-return/zero-state guards in low-flow/invalid-state paths.
3. `src/wshirs.for` observability probes.
4. `src/case12.for` denominator/singularity guards with fallback state hold.
5. `src/hydchn.for` iteration guard caps.
6. `src/makefile` gfortran observability flags.
7. `src/pmxelm.inc`, `src/pmxhil.inc`, `src/pmxpln.inc`, `src/pntype.inc` large dimension increases.

Rollback rationale:
- These patches changed watershed/channel dynamics in ways not yet fully characterized.
- The goal was reduced to the smallest explainable set aligned with the requested rollout sequence.
- The static-dimension changes were removed to avoid accidental `_hill` memory footprint risk.

Rollback verification snapshot (working tree):
- Active source edits are only:
  - `src/newton.for`
  - `src/mann.for`
  - `src/infile.for`
- Previously modified files listed above are no longer modified in `src/`.

---

## Ablation Sequence and Results (Executed)

### Step 1: `newton.for` only
Result on delicate-game replay (`pw0_first301.run`):
- Fails with `SIGFPE` before watershed years run.
- Failure occurs after pass ingestion/output prompt phase.

Interpretation:
- `newton` change did not cause this specific failure.
- Run is blocked earlier by `hmax=0` divide-by-zero path.

### Step 2: `newton.for` + `mann.for` init
Result on same replay:
- Same `SIGFPE` failure point.

Interpretation:
- `mann` init is not sufficient to bypass this dataset’s input fault.

### Step 3: `newton.for` + `mann.for` + `hmax` fast-fail assertion
Result on same replay:
- Deterministic explicit stop with message:
  - `HMAX <= 0.0 ... INVALID PLANT PARAMETER ... PROGRAM STOPPED`
- No ambiguous FP trap stacktrace needed to understand failure.

Input that triggers rejection:
- `/tmp/wepp-debug-delicate/wepp/runs/pw0.man:16`
- Crop block is `Fallow m`; parsed `hmax` value is `0.00000`.
- `cuthgt` for that block is `0.30400` (line 15), which would otherwise yield divide-by-zero in `partcf = cuthgt/hmax`.

Interpretation:
- Fail-fast behavior works as intended.

---

## Observability Verification (Executed)

### Reality check on prior state
- `wepp_observe.on` could be present with no phase log emitted in these triage binaries.
- That was effectively blind for channel-routing stalls.

### New observe log behavior (validated)
Replay:
- `/tmp/wepp-observe-signal-test2/wepp/runs/pw0_first301.run`
- binary: `/workdir/wepp-forest/src/wepp`
- flag file: `/tmp/wepp-observe-signal-test2/wepp/runs/wepp_observe.on`

Observed:
- `wepp_observe.log` created and populated:
  - `/tmp/wepp-observe-signal-test2/wepp/runs/wepp_observe.log`
- Marker stream resolves control flow down to channel segment and case routine.

Build note:
- For deterministic watershed debug binaries, use `make wepp` (not parallel `make all`),
  so watershed include dimensions are not raced against `_hill` include copies.

Crash localization from last marker:
- Last line before SIGFPE:
  - `CASE12_BEGIN y=1 d=62 e=380 c=79 s=8 ...`
- Last completed matching end marker:
  - `CASE12_END ... s=7 ...`

Interpretation:
- The failing execution entered `case12` for channel element `e=380` (channel id `c=79`) at computational segment `s=8` and did not return.
- This is the first concrete, non-guess localization of the current trapped failure.

---

## Ablation Matrix (Executed)

Run root and artifacts:
- matrix root: `/tmp/wepp-ablation-series`
- reference input: `/tmp/wepp-debug-delicate/wepp/runs/pw0_first301.run`
- management input uses corrected `hmax=0.30400`.

Observed matrix summary (`/tmp/wepp-ablation-series/summary.tsv`):
- `dcc52a6`: `rc=0`, success `yes`, last triplet `159/365/3`
- `baseline_observe`: `rc=136`, success `no`, last triplet `59/62/1`, last marker `CASE12_BEGIN ... e=380 c=79 s=8`
- `baseline_finit_local_zero`: `rc=136`, success `no`, last triplet `59/62/1`, last marker `CASE12_BEGIN ... e=380 c=79 s=8`
- `case12_only_guard`: `rc=136`, success `no`, last triplet `155/150/3`, last marker `CHNERO_END ... e=456 c=155`
- `case12_chnrt_hygiene`: `rc=136`, success `no`, last triplet `155/150/3`, last marker `CHNERO_END ... e=456 c=155`

### Compiler init ablation: `-finit-local-zero`
Source delta:
- none (compile-flag-only lane).
- Built with gfortran flags:
  - `-finit-local-zero` added to baseline flag set.

Result:
- No behavioral change on this replay.
- Same signature as baseline:
  - `rc=136`, last `chnwb` triplet `59/62/1`,
  - last marker `CASE12_BEGIN ... e=380 c=79 s=8`.
- Raw output comparison baseline vs `-finit-local-zero` lane:
  - `identical=2113 changed=0`.

Interpretation:
- Uninitialized local scalar state is not the active cause of this specific stall/SIGFPE path.

### Current debug build check: `-O0 + -finit-local-zero`
Replay executed:
- run root: `/tmp/wepp-next-ablation-o0finit`
- command: `/workdir/wepp-forest/src/wepp < pw0_first301.run`

Observed:
- `rc=136`
- last `chnwb` triplet: `59/62/1`
- last observe marker:
  - `CASE12_BEGIN y=1 d=62 e=380 c=79 s=8 ...`

Interpretation:
- Lowering optimization to `-O0` did not shift the failure locus.
- The immediate next ablation target remains localized to `case12` for
  channel element `e=380` at segment `s=8`.

### Candidate A: `case12_only_guard`
Source delta:
- `src/case12.for` only.
- Added denominator guards around the `xde` computation and related divisions.
- Added observe tag `C12_XDE_G` on guard activation.

Result:
- Run progressed far beyond the original early `case12` crash locus.
- `C12_XDE_G` fired repeatedly (`3357` times), typically with `dtcdx-dlat` near `1e-33` to `1e-39`.
- Failure moved downstream to `wshchr` (SIGFPE), not `case12`.

Evidence:
- backtrace top frame maps to `wshchr_` via `addr2line`:
  - `addr2line -f -e wepp_case12_only_guard 0x4a7ca1 -> wshchr_`

### Candidate B: `case12 + chnrt` hygiene
Source delta:
- Candidate A plus `src/chnrt.for` zero-denominator hygiene for `dx`, `wfu`, and `wfl`.
- Added observe tags `CHNRT_DX_G`, `CHNRT_WFU_G`, `CHNRT_WFL_G`.

Result:
- No `CHNRT_*_G` tags fired.
- Failure signature is identical to Candidate A (`rc=136`, same last triplet, same last marker).
- Raw output comparison Candidate A vs Candidate B is exactly identical:
  - `identical=2113 changed=0`.

Interpretation:
- `chnrt` hygiene candidate had no material effect on this replay.

### Parity interpretation for ablation candidates
- Candidate A vs `dcc52a6` and Candidate B vs `dcc52a6`:
  - `identical=2108`, `changed=5` (`chnwb.txt`, `loss_pw0.txt`, `soil_pw0.txt`, `ebe_pw0.txt`, `plot_pw0.txt`)
  - status is `structure_diff` because candidates terminate early (not full-run parity).
- Therefore these parity diffs are not suitable for sediment-regression judgment yet.

### Rollback status after ablation
- Experimental `case12` and `chnrt` ablation edits were rolled back in `src/` after executing the matrix.
- Artifacts remain under `/tmp/wepp-ablation-series` for inspection/replay.

### Updated localization conclusion
- First blocker (baseline): `case12` singular path at `e=380 c=79 s=8`.
- After guarding that path, next blocker is in `wshchr`.
- Next conservative step should target **`wshchr` observability + minimal guard ablation**, not broad channel rewrites.

---

## Sediment Difference Judgment

### What was previously observed
Large sediment/water-balance differences (including `chnwb` storage behavior changes) were observed in an earlier candidate stack.

### Attribution
Those differences were observed while behavioral channel-routing patches (now rolled back) were active.
Given those patches are removed, that prior sediment divergence is **not** evidence against the current minimal patch set by itself.

### Current judgment
- The earlier sediment shifts are best treated as regression signatures from the rolled-back experimental channel guards/short-circuits.
- For the active minimal set (`newton + mann + hmax assert`), delicate-game cannot be used to assess sediment parity until its invalid `hmax` input is corrected or screened upstream.

---

## Release Recommendation (Conservative)
If we ship now, ship only:
- `src/newton.for`
- `src/mann.for`
- `src/infile.for` (`hmax` fail-fast)

Do not ship the rolled-back channel/array-capacity edits without separate ablation and parity evidence.

Operational consequence:
- Scenarios containing `hmax <= 0` now fail fast and must be fixed in input data (or rejected earlier by preflight).

---

## Follow-On Ablation: `wshchr` Integer Overflow (Executed)

### Observe-guided localization
With `case12` guard active and `-O0 -finit-local-zero`, the run moved past the
original `case12` blocker and repeatedly failed in `wshchr`.

Added coarse stage tags:
- `src/wshdrv.for`: `WSHC_BEG`/`WSHC_END` around `call wshchr`
- `src/wshchr.for`: `WCH0`, `WCH1`, `WCH2`, `WCH3`, `WMC0`, and `WSEG`

Critical evidence at the failing element:
- Failing locus: `y=3 d=150 e=457 c=156`
- Last markers before trap:
  - `WCH3 ... v1=5.9254E-11`
  - `WSEG ... v1=3.5552E-08 v2=2.3880E+09`
- Interpretation:
  - `v1` (`dxchr`) becomes extremely small.
  - `v2` (`rseg = chnl1/dxchr`) exceeds 32-bit integer range.
  - Existing code cast `nseg = rseg` directly, triggering `SIGFPE` on real->int overflow.

Same behavior observed later in the run-day stream:
- Example: `WSEG ... e=457 ... v2=1.3380E+13` (even larger overflow risk).

### Why `dxchr` got tiny, and whether clipping is intended
Key equations in `wshchr`:
- `dxchr = dtchr * ckref`
- `rseg = chnl1 / dxchr`
- `nseg` is the integer segment count used for routing loops.

What observe values showed at the failing locus (`e=457`):
- `WCH1` (`qref`) was near zero (`~7e-19`).
- `WCH2` (`y`) was near zero (`~3.9e-6`).
- `WCH3` (`ckref`) was near zero (`~5.9e-11`).
- Therefore `dxchr` became extremely small (`~3.6e-08`), and `rseg` exploded (`~2.4e+09` then `~1.3e+13`).

Interpretation:
- This is a near-dry hydraulic state where celerity collapses, not a physically meaningful request for billions of routing segments.
- The model’s compile-time cap already encodes intended bounds: `mxcseg=101` in `pmxcsg.inc`.
- So the intended behavior is to cap discretization to `1 <= nseg <= mxcseg`; the bug was only that conversion to integer happened before enforcing that cap.

Implication of the patch:
- No new physical cap was introduced; it enforces the existing cap safely.
- For normal in-range cases, behavior is unchanged.
- For pathological tiny-`dxchr` cases, behavior becomes deterministic (saturate to `mxcseg`) instead of trapping.

### Targeted patch (minimal behavioral change)
File: `src/wshchr.for`

Before:
- `nseg = rseg`
- followed by post-cast bounds checks (`if(nseg > mxcseg)...`, `if(nseg < 1)...`)

After:
- clamp in real domain before casting:
  - `NaN -> nseg = 1`
  - `rseg >= float(mxcseg) -> nseg = mxcseg`
  - `rseg <= 1. -> nseg = 1`
  - else `nseg = int(rseg)`

Why this is safer:
- Preserves original intent (`1 <= nseg <= mxcseg`) for finite values.
- Removes undefined/overflowing intermediate conversion.
- Avoids trap sensitivity to compiler/runtime conversion behavior.

### Result
Replay with patch:
- run root: `/tmp/wepp-next-ablation-wsegfix`
- command: `../wepp < pw0_first301.run`
- return code: `0`
- stdout includes:
  - `WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY`

Conclusion:
- Next ablation target identified and resolved.
- The observed stall/trap in this lane was not a watershed "hang"; it was a deterministic
  floating-point trap caused by out-of-range real->integer conversion in `wshchr`.

### Updated conservative ship set
For this failure mode, minimal justified set is now:
- `src/newton.for`
- `src/mann.for`
- `src/infile.for` (`hmax` reject)
- `src/wshchr.for` (pre-cast `nseg` clamp)
- `src/wshdrv.for` and `src/wshchr.for` observe markers (debug-only effect, gated by `wepp_observe.on`)

---

## Compiler Optimization Decision and Timing (Executed)

### Why this was revisited
`-O0` was useful for localization and observe-driven ablation, but it made candidate
runtime materially slower. We reran with `-O2` to check whether performance improves
without reintroducing instability or changing outputs materially.

### Build/runtime lanes compared
- Baseline binary: `wepp_dcc52a6`
- Candidate debug lane: gfortran `-O0 -finit-local-zero`
- Candidate optimized lane: gfortran `-O2 -finit-local-zero`

Source code was unchanged between candidate `-O0` and candidate `-O2`; only compiler
optimization level changed.

### Full replay timing (hillslopes + watershed)
Replay protocol:
- `p1..p301` hillslopes, then `pw0.run` watershed
- input set from delicate-game replay workspace

Observed wall times:
- `wepp_dcc52a6`: `166 s`
- candidate `-O0`: `1331 s`
- candidate `-O2`: `862 s`

Interpretation:
- `-O2` recovers substantial performance vs `-O0` but remains slower than `dcc52a6`.

### Watershed-only timing (`pw0.run`) with observe explicitly OFF
To isolate watershed runtime, we benchmarked only `pw0.run` with repeated runs (`n=3`)
and with `wepp_observe.on` removed for candidate lanes.

Artifact:
- `/tmp/wepp_watershed_bench.tsv`

Results:
- `dcc52a6`: min `28.37 s`, median `29.21 s`, mean `29.07 s`, max `29.64 s`
- candidate `-O0`: min `54.40 s`, median `54.95 s`, mean `54.89 s`, max `55.33 s`
- candidate `-O2`: min `36.86 s`, median `37.09 s`, mean `37.09 s`, max `37.31 s`

All runs:
- `rc=0`
- watershed success marker present.

Relative performance (median):
- candidate `-O2` vs candidate `-O0`: ~32.5% faster
- candidate `-O2` vs `dcc52a6`: ~27.0% slower

### Output stability check: `-O2` vs `-O0`
Strict raw compare on `ebe_pw0.txt`, `loss_pw0.txt`, `chnwb.txt`:
- `chnwb.txt`: identical
- `ebe_pw0.txt`: 1 differing numeric value (`max_abs=0.21`)
- `loss_pw0.txt`: 6 differing numeric values (`max_abs=0.1`)

Interpretation:
- Candidate `-O2` and candidate `-O0` are effectively output-equivalent for this run.

### Output parity check: candidate `-O2` vs `wepp_dcc52a6`
Diff profile matches candidate `-O0` vs `wepp_dcc52a6`:
- same changed-file set and same dominant event-level differences
- annual outlet-summary deltas unchanged from prior candidate-vs-baseline readout.

Interpretation:
- Optimization level (`-O0` vs `-O2`) is not driving the candidate-vs-baseline
  scientific parity differences for delicate-game; those differences come from
  the active source patch set.

### Decision
For this incident patch line, use candidate builds at:
- gfortran `-O2 -finit-local-zero`

Rationale:
- materially better runtime than `-O0`
- no meaningful candidate-internal output drift vs `-O0`
- preserves observed stability fix behavior.
