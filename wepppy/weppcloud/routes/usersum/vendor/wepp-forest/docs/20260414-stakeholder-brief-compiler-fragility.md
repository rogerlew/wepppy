# Stakeholder Brief: Modernizing the WEPP Build — What Changed, Why, and What to Expect

Date: 2026-04-14 (revised 2026-04-26)
Audience: Hydrologists, land managers, program staff, and analysts who use WEPP results

## The short version

WEPP's physics has not changed. What changed is the modern toolchain we now use to compile the WEPP model from its FORTRAN source into the executable that actually runs on our servers.

For roughly thirty years, WEPP was compiled with an older Intel FORTRAN compiler that quietly tolerated a handful of rare numerical edge cases — moments during a long simulation where the math briefly asks something the program cannot cleanly answer (divide by zero, a layer index that falls just outside the soil profile, a channel velocity so small it overflows an integer counter). The old compiler let those moments slide, often producing a plausible-looking number without any guarantee it was correct.

Modern compilers on our current Linux servers can be told to stop a run the instant one of those moments occurs. The stop takes the form of a specific signal called **SIGFPE** (signal: floating-point exception) — the operating system's way of reporting that the program just asked for an arithmetic operation with no valid answer, such as dividing by zero, overflowing a numeric range, or taking the square root of a negative number.

**We made a deliberate engineering decision to stop tolerating SIGFPE** rather than ignore it, because tolerating it has three costs we are no longer willing to pay:

- **Silent corruption.** When a floating-point exception is ignored, the arithmetic unit produces a sentinel value (infinity, NaN, or an undefined bit pattern) and the program keeps going. That value can flow through dozens of downstream equations before it shows up in a plot or a summary, at which point the originating cause is nearly impossible to trace. A crash at the source is far better than a quietly wrong answer that looks plausible in a report.
- **Non-determinism.** Different compilers, different optimization levels, and even different CPUs can make different choices about what "ignoring" a floating-point exception means. A run that produces one number today could produce a different number tomorrow for reasons unrelated to the physics. Trapping the exception at its source removes that variability and makes WEPP reproducible across machines and rebuilds.
- **Debuggability.** When the program stops at the exact instruction that caused the problem, we can see the run, the simulation day, the hillslope or channel element, and the offending state. That is how every fix described below was isolated. Without SIGFPE enforcement, the same investigations would take weeks of guessing instead of hours of evidence-gathering.

The trade-off is real: as we moved to the new build environment, a small number of watersheds started failing mid-simulation on days or events where they used to finish. Each of those failures, however, points at a specific defect we can now see and repair — defects that were always producing suspect numbers in the old binary, but were invisible. Our response has been deliberately narrow: identify each failing edge case, add a targeted guard so the model handles it predictably, and leave the rest of the physics alone. You should expect substantially more reliable runs and, in a small number of boundary situations, slightly different numbers than the old binary produced.

## How we investigate each failure: ablation testing

When a run crashes with SIGFPE, we do not patch it by intuition. We run an **ablation campaign** — a structured investigation that changes one variable at a time until the exact cause is isolated on the record. The word "ablation" here is borrowed from the experimental sciences: remove or alter one element, hold everything else constant, observe the result, and draw a conclusion you can defend.

Each campaign is a formal **work package** owned by a coding agent (Codex) and supervised through [docs/ablation/protocol.md](ablation/protocol.md). The workflow runs autonomously and is the same every time:

1. **Reproduce the failure.** Copy the failing run's inputs to a staging directory — the original files under `/wc1/runs/...` are never mutated in place. Capture the exact command, the binary identity (path, compiler, build flags), the full standard-error log, and the operating-system signal that was raised. If we cannot reproduce the failure from a clean environment, we do not proceed.
2. **Add observability before adding fixes.** WEPP now ships with an opt-in diagnostic logger. Before hypothesizing a cause, we enable it and add coarse phase markers around the suspected failure boundary so the log records the last successful simulation year, day, hillslope, channel element, and segment before the crash. This converts "it crashed somewhere in routing" into "it crashed at year 24, day 69, element 8, inside the frost-layer lookup."
3. **Form evidence-backed hypotheses.** Every hypothesis must cite a concrete signal from the logs — the last marker before the trap, a specific stack frame, a denominator value captured at runtime. Intuition alone is not grounds for a patch.
4. **Design ablation lanes.** The investigator lays out a matrix of single-variable experiments: one row per run, one cell per independent change. Lane 0 is always the unmodified baseline. Subsequent lanes change exactly one thing — a simulation-year limit, a single output toggle, a single soil-layer bound, a single candidate guard. Behavioral changes are never combined until earlier lanes prove each one is necessary.
5. **Execute and classify.** Every lane is run, and its outcome is recorded as *no effect*, *progress shift* (failure moved to a later phase), *resolved*, or *regression*. A "no effect" result is just as important as a fix — it rules out an entire class of hypotheses and is preserved in the record.
6. **Keep or roll back.** Any change that does not measurably improve stability, model intent, or correctness is rolled back. This prevents speculative edits from accumulating in the codebase.
7. **Publish the evidence.** Every campaign produces an **incident package** — a self-contained folder under [docs/ablation/](ablation/) named after the run, the failure scope, and the failure signature (e.g., `20260419_operational-berry_pw0_sigfpe-locate-frostn`). It contains:

   - **`incident.md`** — the decision record: what failed, where, the baseline reproduction command, the ablation findings, the chosen fix, the rollback plan.
   - **`matrix.csv`** — one row per experimental run, with immutable case identifiers, the exact mutation, pass/fail outcome, failure signature, and paths to the logs.
   - **`notes.md`** — the chronological operator log with timestamped commands and observations.
   - **`artifacts/`** — the raw evidence: stdout/stderr logs for every run, input-file diffs, copies of the reproduction inputs, environment metadata (host, container, binary build info), a manifest listing every artifact, and a checksum file so anyone can verify nothing has been altered after the fact.

   An independent reviewer can open any incident folder, re-run the baseline case with the recorded command, observe the same crash, apply the documented change, and confirm the same fix.

## Parity testing against canonical binaries

A fix that stops a crash is only half the story. Before any new binary is released, it is compared against a **canonical reference binary** on the same inputs to confirm the fix did not quietly change results where it was not supposed to.

Our canonical references are:

- **`wepp_dcc52a6`** — the legacy baseline that reproduces historical outputs used in the published literature. Treated as the scientific ground truth for workloads that do not need recent feature additions.
- **The IFX (Intel Fortran) Windows build** — an independent toolchain compiled from the same source. Used as a cross-compiler witness: if the Linux guarded build and the IFX build agree in aggregate on the same staged run, we have strong evidence that the results reflect the model's physics rather than one compiler's quirks.

Parity is evaluated at two levels:

- **Raw parity.** Every output file (`chnwb.txt`, `ebe_pw0.txt`, `loss_pw0.txt`, `soil_pw0.txt`, and so on) is compared byte-for-byte. This is the strictest possible test and typically identifies a small number of changed files, with most files identical.
- **Meaningful parity.** Numeric values are compared under hydrology-appropriate tolerances — for example, one percent relative tolerance for water variables and ten percent for erosion variables, which reflects the inherent spread of the underlying processes. This test asks the question stakeholders actually care about: *do the new numbers tell the same story as the old numbers?*

The April 2026 cross-compiler parity report is an example. The Linux guarded build and the IFX Windows build, run on the same staged watershed, both completed without SIGFPE. Raw parity showed four changed files out of 237. Meaningful parity showed that roughly 0.2 percent of channel-water-balance values and 0.1 percent of event-by-event erosion values exceeded the strict tolerance bands — all concentrated on a small number of boundary days. Aggregate drift across the entire simulation was on the order of one part per million. That is the level of agreement we accept as "the two compilers are telling the same hydrologic story," and it is the explicit bar a guarded build must clear before it is promoted to a release.

## Why this is a modernization, not a rewrite

The old compiler ran in an environment that is no longer available on modern hardware. Keeping WEPP alive on current operating systems, current CPUs, and current scientific workflows requires a modern compiler. We did not choose to rock the boat; we chose to keep WEPP running.

When we rebuilt the same FORTRAN source with a modern compiler, three things happened:

1. The model ran faster and on a wider range of hardware.
2. A handful of long-latent bugs in the code became visible as crashes. These bugs were always there; they were simply masked for decades by the old compiler's tolerance for undefined math.
3. The bit-for-bit output for some edge-case days drifted slightly, because the modern compiler can no longer "improvise" an answer at an undefined moment.

All three of those outcomes are expected when any long-lived scientific code moves to a modern compiler. The same pattern has played out in other long-lived simulation codes (climate models, CFD codes, reservoir simulators) as they modernized.

## What we actually fixed

Each fix below came out of a formal "ablation campaign": an evidence-driven investigation that isolates the exact trigger (run, year, day, hillslope, channel element), confirms the minimal code change that resolves it, and documents the residual risk. None of these changes alter WEPP's hydrologic or erosion physics. They guard specific numerical edge cases so the model does not crash on them.

### 1. Plant input validation (`hmax = 0`)

Some management files contained a plant canopy maximum height of zero. The old code silently divided by that zero and continued with an undefined value. The new build now stops immediately and reports the invalid input so it can be corrected upstream.

Impact: runs with this bad input now fail loudly instead of silently producing questionable output.

### 2. Newton-solver termination (`newton.for`)

An interior solver could, in rare states, iterate without converging — producing what looked like a hung run. It is now bounded (guaranteed to terminate) and clamped to physically meaningful values.

Impact: eliminates "stuck" watershed runs. The iteration path differs slightly from the legacy solver near difficult inputs, which can shift a small number of event-level values.

### 3. Manning's-equation initialization (`mann.for`)

A piece of the channel-hydraulics routine relied on the compiler to zero out certain working variables on first use. The old compiler did that by default; modern compilers do not. The routine now initializes those variables explicitly.

Impact: deterministic, repeatable behavior across compilers. No change to the physics.

### 4. Channel-segment overflow (`wshchr.for`)

In near-dry conditions, channel celerity can collapse to a very small number, which would make the code ask for billions of routing sub-segments. The internal cap on segment count (`mxcseg = 101`) was the intended physical bound all along, but the old conversion to integer happened before the cap was enforced and could overflow on modern hardware. The cap is now enforced first.

Impact: near-dry channel days are now handled deterministically at the intended discretization cap. No change for normal flows.

### 5. Frost-layer indexing (`locate.for` — operational-berry incident)

During frost and winter processing, the soil-layer lookup could request a layer one index past the bottom of the profile. The old code crashed on that request under modern traps; the new code clamps the lookup to the actual bottom layer and guards the denominator terms that depend on it.

Impact: resolves the frost-season SIGFPE that was blocking larger watersheds. Results are preserved for all in-bounds requests; for the rare out-of-bounds request, the model now uses the bottom-layer values instead of crashing.

### 6. Watershed routing denominators (`wshdrv.for`, suppurative-skunk incident)

The watershed routing path in a particular run hit a near-zero denominator starting in simulation year 13. A data-triggered numeric guard now prevents the trap at that location. The guarded binary completes the full 300-year simulation cleanly.

Impact: previously blocked run now completes. Aggregate outputs are close to what the legacy path produced on non-failing years, with small event-level differences on the guarded days.

### 7. Dry-watershed rise-time ratio (`wshpas.for` — upstream-scheme incident)

In dry or no-flow watershed years, two accumulators (`qptsum` and `qpsum`) can both legitimately remain at zero for the entire year. The code then computed a storm hydrograph rise-time ratio as zero divided by zero, which is mathematically undefined and crashed the run under modern floating-point checking. The new build recognizes the zero-flow condition and substitutes a rise-time of zero — the physically correct answer for a year with no watershed flow — instead of attempting the undefined division.

Impact: desert and other dry-climate watersheds that previously crashed during simulation now complete. A five-watershed parity panel spanning humid, snow-dominant, seasonal marine, and mixed-mountain climates confirmed the guard never activates outside of genuine zero-flow conditions; wet-climate results are byte-for-byte unchanged against the pre-guard modern build.

### 8. Parameter-routine denominator (`param.for` — p325 incident)

A continuity ratio in hillslope parameter initialization could collapse near zero. A defensive guard was added matching the style already present for a sibling expression in the same routine.

Impact: closes a historically observed production crash path without changing results for well-conditioned inputs.

### 9. Frost-season soil-water arithmetic (`saxfun.for` — primitive-hug incident)

A second frost-season failure surfaced inside the same winter-processing call chain as the operational-berry fix, but in a different routine. A soil-water-distribution helper (`saxfun`, reached from `watdst` during frost processing) was performing power and divide operations on soil-property terms — layer index, soil moisture, porosity, density, and the curve exponent — that can legitimately reach degenerate values in a frost-affected layer (a thin or fully frozen layer where moisture, porosity, or density approach the limits of their physical range). Under those degenerate inputs the modern build raised SIGFPE; the legacy build silently produced an undefined number and continued.

The patch adds narrow domain guards at each of those operations so they always evaluate on physically meaningful inputs. Specifically:

- **Layer-index guard.** If the requested soil layer falls outside the actual profile (less than 1 or greater than the layer count), the routine returns the standard "no contribution" sentinel pair — water potential of −150 kPa (the dry-end limit the surrounding code already understands) and a zero unsaturated-conductivity contribution — instead of indexing past the array.
- **Negative-moisture clamp.** If the incoming soil-moisture term arrives slightly below zero (a numerically degenerate state, not a physical one), it is clamped to zero before being used in any later term. This is the same convention the rest of the soil-water code already uses for moisture inputs.
- **Zero-porosity guard.** If the porosity for the requested layer collapses to effectively zero, the routine again returns the dry-end "no contribution" sentinel pair rather than dividing by it.
- **Near-zero denominator guard in the wet-end branch.** In the branch that interpolates water tension between 33 kPa and 0 kPa, if the denominator collapses to effectively zero, the water-tension contribution is set to 0 (the wet-end limit) instead of dividing by an effectively-zero number.
- **Zero-base / negative-exponent guard.** The conductivity term raises a moisture ratio to a curve exponent. If the ratio is effectively zero *and* the exponent has gone negative — the one combination that mathematically blows up (zero to a negative power is infinity) — the conductivity contribution is set to zero rather than evaluated. All other combinations are computed normally.

Each guard also emits a labeled observability marker so we can see, after the fact, which guard branch (if any) actually fired during a run.

Impact: a watershed run that previously crashed reproducibly during a frost-season day now completes cleanly. The guard branches only activate on the degenerate inputs that previously crashed, so well-conditioned frost-season days are unaffected.

### 10. Hourly inter-layer seepage at an impermeable boundary (`perc.for` — exorbitant-affidavit incident)

This is the first failure documented in this brief that originates in the **hillslope binary** rather than the watershed binary. The trap was raised inside the hourly water-balance update (`perc -> purk -> watbal_hourly`), in the expression that computes the saturated seepage rate between a soil layer and the layer immediately below it.

That expression is a harmonic mean of the two adjacent layers' saturated conductivities — the standard way to combine conductivities of two materials in series. When the layer below has a saturated conductivity of zero, which is how an effective bedrock or impermeable boundary is encoded in the soil profile, the harmonic mean is mathematically undefined (the divide-by-zero appears inside the harmonic-mean denominator). The legacy compiler silently produced an unconstrained number; the modern build raised SIGFPE the moment the equation was evaluated.

The patch adds a single guard in the affected branch: if either of the two layers' saturated-conductivity terms is nonpositive, the inter-layer seepage rate is set to zero — the physically correct answer when no water can pass into the layer below — instead of evaluating the harmonic-mean expression. The guard emits a labeled observability marker on activation.

A sibling-arithmetic audit was performed across every divide and power site in the same routine: only this expression matched the observed fault pattern, and the audit table is preserved in the incident folder.

Impact: the originally failing hillslope completes its full simulation cleanly. A broader screen across the run-archive flagged seven additional hillslopes in the same run that exhibited the identical fault chain; all eight resolve under the same one-line guard with no further changes. Parity against the canonical `wepp_dcc52a6` reference shows aggregate drift on the patched run on the order of one part per million for water-balance and erosion totals, with sparse local exceedances explained by output-shape additions in the modern build (new `TSMF`, `QRain`, `QSnow` columns) and a stable parameter offset (`Kr` 0.13 vs 0.12) that pre-dates this guard.

### 11. Zero-duration runoff event in time-of-concentration (`wshpas.for` — srivas42-combatant-ionosphere incident)

This is a second, distinct guard in the same routine as fix #7, at a completely different expression. Where fix #7 handled the rise-time ratio in zero-flow years, this one handles the per-event time-of-concentration calculation when an individual runoff event has a recorded duration of zero but a non-zero runoff volume — a pairing the legacy compiler tolerated but that is mathematically a divide-by-zero.

The time-of-concentration formula raises the runoff intensity (volume divided by duration) to a fractional power and multiplies by a slope term to a different fractional power. When a runoff event arrives with `dur = 0` and non-zero runoff (the failure boundary observed in the incident was the very first routed event of the simulation), the intensity term is undefined and the modern build raises SIGFPE the moment it is evaluated.

The patch adds four narrow guards in the affected event block:

- **Zero-duration intensity guard.** If the event duration is at or below a small numeric floor while runoff is non-zero, the intensity term is treated as zero rather than evaluating the divide. This matches the routine's pre-existing convention of clamping near-zero denominators with the same floor.
- **Non-positive slope guard.** A defensive guard on the slope term used in the same expression, in case it ever arrives at or below zero. The marker did not fire on the originating run; it is held in place as same-expression sibling protection.
- **Composite-denominator guard.** The combined denominator that feeds the time-of-concentration is also floor-protected. As above, the marker did not fire on the originating run; held as sibling protection.
- **Downstream zero-volume guard.** A subsequent expression in the same block divides by total runoff volume; that site receives the same floor treatment with an `oalpha = tcs / 24.0` fallback that the routine already used elsewhere for the analogous condition.

The guarded expression is the only site in this block that fired on the originating run; the other three are belt-and-suspenders for arithmetically equivalent siblings identified by an audit recorded in the incident folder.

Impact: the originally failing hillslope completes its full simulation cleanly. A control hillslope from the same run that did not exhibit the fault remains byte-identical against the pre-guard build (7 of 7 output files), confirming the guards activate only on the failing condition and do not perturb normal events.

### 12. Hourly water-balance hydraulic calibration (`watbal_hourly.for` — twenty-two-fratricide / unveiled-grinder incident)

This is a second failure in the hillslope binary (following fix #10), surfacing in a different routine than the inter-layer seepage guard. The trap was raised inside the hourly water-balance routine during hydraulic initialization, in the expression `hk = -2.655 / alog10(fc/ul)` — a calibration formula that derives a per-layer hydraulic adjustment from the ratio of field capacity to saturated water content. When a soil layer has a field capacity of zero while saturated water content is positive, the ratio `fc/ul` evaluates to zero, and `alog10(0.0)` is mathematically undefined. The legacy compiler silently propagated the result; the modern build raises SIGFPE the moment the logarithm is evaluated.

The diagnostic observability lane confirmed the exact boundary before any patch was applied: the last marker before the trap recorded `fc = 0`, `ul > 0`, `ratio = 0.0` at the hk initialization site in `watbal_hourly`. A narrow guard now tests `fc/ul` before the logarithm: when the ratio is zero or negative — meaning no physically meaningful positive ratio exists for the calibration expression — `hk` is set to zero rather than evaluating the undefined logarithm. All layers with positive field capacity continue through the original formula unchanged. The guard emits an observability marker on activation so the condition remains visible in future diagnostic runs.

A compiler-provenance check was performed alongside the guard: the prior release binary was linked against a Homebrew-supplied interpreter rather than the system loader. The guarded binary was rebuilt with the pinned system compiler (`/usr/bin/gfortran`) and confirmed to preserve the same fix behavior under both compiler targets. All binary gates passed — readelf interpreter, smoke, reconciled-condenser replay, and the full pytest suite (43 passed) — before promotion.

Impact: both originally failing hillslopes (`twenty-two-fratricide:p258`, `unveiled-grinder:p1319`) complete their full simulations cleanly. The guard activates only on layers with zero or negative field capacity; well-conditioned inputs are unaffected. Release target is `wepp_260425` and `wepp_260425_hill`, built with the pinned system compiler.

### 13. Non-hourly water-balance hydraulic calibration (`watbal.for` — taken-brainstem incident)

This is the sibling guard to fix #12, applied to the **non-hourly** `watbal` routine. The same expression — `hk = -2.655 / alog10(fc/ul)` — appears in both `watbal_hourly` (guarded by fix #12) and in the non-hourly `watbal` path, which remained unguarded until this incident surfaced.

The `taken-brainstem:p1408` hillslope failed with SIGFPE on the current release binary (`wepp_260425_hill`). Address translation localized the trap to `watbal_` rather than `watbal_hourly_`, confirming a distinct and unguarded site with identical arithmetic structure: when a soil layer has zero field capacity (`fc = 0`) while saturated water content is positive (`ul > 0`), the ratio evaluates to zero and `alog10(0.0)` is undefined. The observability lane confirmed the exact state before the crash — `fc = 0`, `ul > 0`, `ratio = 0.0` — at the hk initialization site in `watbal`.

The patch applies an identical guard to the non-hourly path: when `fc/ul <= 0`, `hk` is set to zero rather than evaluating the logarithm. A fuzzy regression across 11 hillslope seeds — including the p258 and p1319 seeds from fix #12 — introduced no regressions; all comparator-pass seeds remained passing, and the incident seed improved from FAIL to PASS.

Impact: the `taken-brainstem:p1408` hillslope completes its full simulation cleanly. The guard activates only on layers with non-positive `fc/ul`; well-conditioned inputs continue through the original formula unchanged.

### 14. Built-in observability for future incidents

We added an optional, off-by-default diagnostic log that records exactly which phase of the simulation was executing when a run fails. This is how we were able to localize the fixes above to specific channel elements, hillslopes, days, and years within long simulations. It has no effect on results when it is off.

## Going on offense: generative input testing

The thirteen fixes above came out of **reactive** work — real production runs crashed, and we followed each crash back to its cause. That is necessary but not sufficient. The same discipline we use to investigate a known failure can be turned around and used to *hunt for the next one* before a user ever sees it.

This is the purpose of our **generative input fuzzing** program. "Fuzzing" is a software-engineering term for a stress test: the model is run, at scale, on thousands of plausible-but-deliberately-pressured input sets, each one designed to probe a specific class of numerical edge case. Any case that produces a crash, an invalid number, or a nonsensical output is captured, minimized into a minimum reproducing example, and fed into the same ablation discipline used for real incidents. The goal is to find and close the next boundary defect while it is still cheap to fix, instead of waiting for it to surface in a production watershed.

### What "single-OFE" means and why we started there

A WEPP hillslope is represented as one or more **Overland Flow Elements** (OFEs) — independent strips of land that share a slope profile, a soil profile, and a management profile. A **single-OFE** run is the simplest valid configuration: one strip, one soil, one management, one climate. A **multi-OFE** run stacks several strips in series so water, sediment, and cover state pass from the upslope element to the next.

We deliberately scoped the first full year of generative testing to single-OFE runs only. The reasoning is the same reasoning that drives ablation testing: change one variable at a time. A single-OFE run has every ingredient that can trigger a numerical edge case — soil physics, management events, climate events, slope response, water balance — but none of the cross-element interactions that make a multi-OFE failure hard to attribute. If we can prove the model is stable on the simplest executable configuration, any remaining multi-OFE failure we later find is provably a property of the coupling between elements, not of the elements themselves. That is a much cleaner investigation than trying to untangle a ten-element hillslope crash from scratch.

The scope is mechanical, not philosophical: of roughly seventy-one thousand real run signatures discovered in our production archive, about sixty-nine thousand were structurally single-OFE and eligible for the campaign; the rest were explicitly quarantined for a later multi-OFE pilot.

### How the campaign works

The program is built in three layers, each feeding the next:

1. **Wrapper contract checks.** Before any WEPP binary is called, every piece of Python code that *writes* a WEPP input file is tested to guarantee it round-trips cleanly, serializes deterministically, and fails loudly on malformed input. Without this layer, a binary crash could be blamed on a bad input writer rather than on the model itself. These checks eliminate that ambiguity.
2. **Constrained input generators.** Real production inputs are used as **seeds** — we do not fabricate soils or management files from scratch. The generators mutate real seeds along carefully chosen dimensions (soil texture, conductivity, layer density, event duration, slope response), producing inputs that are *plausible* but deliberately pushed toward known numerical edges. Aggressive pre-filtering is intentionally avoided: if a combination is physically unusual but the parser accepts it, the model should survive it.
3. **Trap-enabled binary campaigns.** Every generated input set is executed against the modern, strict WEPP binary — the same build that raises SIGFPE on undefined math — and the result is parsed, classified, and clustered. Crashes are binned by the routine they originated in; outputs are scanned for invalid numbers even when the process exited cleanly.

### Coverage: climate and slope stratification

A single-OFE campaign that only sampled wet, gentle-sloped hillslopes would tell us nothing about dry, steep ones. To force real coverage, every campaign allocates a mandatory quota of cases across a **three-by-three grid** of climate regime (dry, mesic, wet — split on annual precipitation terciles) and slope regime (gradual, moderate, steep — split on slope terciles). A minimum number of cases must complete in every one of the nine bins before a campaign is allowed to report a result. This is how we avoid over-confident "no failures" claims that are really "no failures *in the half of the grid we sampled*."

### Pressure profiles: where we push

Random perturbation of soil and management inputs produces mostly uninteresting runs. To concentrate pressure on the parts of the model most likely to behave badly, each case is additionally tagged with one of five **mutation-pressure profiles**, each targeting a different failure mechanism:

- **P1 — denominator-edge stress.** Push scalar inputs toward near-zero regions where any dividing expression can overflow or go undefined.
- **P2 — event-edge stress.** Bias management and event timing toward short, spiky, or degenerate events (for example, a zero-duration runoff event) to stress transition logic.
- **P3 — conductivity/saturation contrast.** Pair extreme conductivity values with extreme saturation values in the same soil layer to stress water-balance transitions.
- **P4 — texture/density discontinuity.** Put abrupt contrasts between adjacent soil layers to stress interpolation and transition logic.
- **P5 — slope-response amplification.** Bias seed selection toward upper-slope tails within each slope bin to increase exposure of slope-coupled paths.

Cases that fire multiple warnings from the input-quality checks, or whose lineage has produced novel signatures in prior runs, are **adaptively oversampled** on subsequent runs so finite compute budget is spent where the signal is.

### Two guardrails: are we actually sensitive?

A campaign that always reports "no failures found" is worthless if we cannot verify that it would detect a failure if one existed. Two independent guardrails are mandatory on every run:

- **Positive controls.** A small set of known historical failures (the same ones documented in the ablation incident folders) is injected into every campaign. If any injected failure is not classified correctly, the campaign fails its sensitivity gate and no results are reported. In every run of record to date, all five required controls were detected.
- **Second-opinion output oracle.** Independent of whether the process crashed, every output file from every completed run is scanned for invalid numeric tokens (`NaN`, `Inf`), impossible-for-the-field negative values, and unparseable rows. A run that exits cleanly but produced a NaN somewhere in its output is flagged just as loudly as a crash. This is critical: the old compiler's chief failure mode was producing a plausible-looking number that was actually corrupt. The output oracle is the defense against the same pattern reappearing at a new site.

### What the campaigns found, and what we patched

The campaign scaled in four stages. The first two rounds (108 cases at baseline, 216 cases under amplified pressure) returned clean — every case passed. The third round, now scaled to 1,008 cases and fitted with the output oracle, surfaced 140 cases where the model completed but its outputs contained `NaN` tokens in channels used by downstream analysis (`.wat.dat`, `.element.dat`, and occasionally `.soil.dat`). All 140 were triaged to **true numeric instability** rather than cosmetic log-text artifacts, and clustered into nine **priority slices** — specific intersections of a climate bin, a slope bin, and a pressure profile that concentrated the failures.

The nine open slices, and their closure outcomes, are:

| Slice | Pre-patch | After targeted patches | Final status |
|---|---|---|---|
| `wet / moderate / P5 slope amplification` | 61 / 200 | 24 / 200 | **accepted upstream** |
| `wet / steep / P5 slope amplification` | 76 / 200 | 22 / 200 | **accepted upstream** |
| `dry / steep / P5 slope amplification` | 30 / 200 | 0 / 200 | **patched** |
| `wet / gradual / P5 slope amplification` | 45 / 200 | 8 / 200 | **accepted upstream** |
| `mesic / gradual / P5 slope amplification` | 45 / 200 | 0 / 200 | **patched** |
| `dry / moderate / P2 event edge` | 20 / 200 | 0 / 200 | **patched** |
| `wet / moderate / P2 event edge` | 70 / 200 | 20 / 200 | **accepted upstream** |
| `wet / steep / P4 texture/density discontinuity` | 72 / 200 | 31 / 200 | **accepted upstream** |
| `dry / steep / P4 texture/density discontinuity` | 38 / 200 | 0 / 200 | **patched** |

Four slices reached the frozen closure criterion — **two consecutive two-hundred-case reruns with zero non-pass outcomes** — and are marked **patched**. Five remained symptomatic after a bounded patch attempt and are marked **accepted upstream**: the symptom was materially reduced, the reproducer is deterministic and preserved, and the remaining cases will be addressed by a deeper investigation (likely a narrow Fortran-side guard, in the same ablation discipline used for the thirteen fixes earlier in this brief) rather than by further input-wrapper clamping.

Across the full 1,008-case calibrated rerun after patches landed, the composite non-pass rate fell from **134 cases to 41 cases** — a **70 percent reduction** — with the positive-control sensitivity gate still passing at 5 of 5. The three pressured profiles dropped as follows: slope amplification 60 → 11, event-edge 33 → 4, texture/density discontinuity 34 → 8.

### What the patches actually are (and what they are not)

It is important to be precise about *where* the Milestone 7 patches live. Unlike the thirteen fixes earlier in this brief — each of which is a defensive guard inside a specific Fortran routine — **the fuzzing-driven patches landed so far are in the Python input-generation layer**, not in the WEPP binary. Specifically:

- The **slope-response amplification** patch constrains the mutation generator so saturation, texture fractions, and bulk density cannot co-amplify past ranges that produce unphysical soil profiles under extreme slope bias.
- The **event-edge** patch constrains management-mutation windows so generated events stay within safe temporal bounds (no zero-duration, non-zero-intensity pairings of the kind that caused the `wshpas` time-of-concentration crash in the ablation work).
- The **texture/density discontinuity** patch bounds the sum of adjacent-layer texture perturbations so generated profiles remain structurally coherent.

Each patch has a dedicated regression test that locks in the clamp behavior. None of them alter the WEPP model; they alter the fuzzer so it stops generating inputs that are outside the documented contract of the model in the first place. Where the fuzzer's clamp is not enough — the five **accepted-upstream** slices — the remaining failures are being promoted into the ablation track for Fortran-side investigation on the next cycle.

That promotion has begun. A dedicated ablation campaign targeting the three wet-climate P5 slope-response slices (`wet/gradual`, `wet/moderate`, `wet/steep`) completed on 2026-04-22. Four hypothesized Fortran-side mechanisms were tested one at a time in isolated lanes against a matched 120-seed subset — the `route` routine's denominator boundary, the `irdgdx` denominator paths in `sloss`, the kinematic-wave slope-coupled arithmetic in `unifor`, and the Manning-path arithmetic in `mann`. Every behavioral lane produced a result numerically identical to the observability-only baseline. None of the four candidate mechanisms attributed the failure, and all four candidate edits were rolled back rather than merged. The empty patch set is the correct outcome when no lane demonstrates measurable causal attribution under matched seeds — it is the same keep-or-roll-back discipline applied to the thirteen Fortran fixes earlier in this brief, running in the direction of *negative* evidence. The investigation did surface a new lead: a runtime-error signature repeatedly mapping to an end-of-file read path (`stmget.for` line 122), which will be the next cycle's first hypothesis. The remaining two accepted-upstream slices — the wet/moderate P2 event-edge slice and the wet/steep P4 texture/density slice — have not yet had their own ablation packages and are next in the queue under the same one-mechanism-per-lane protocol.

### Why this matters for stakeholders

- **Proactive coverage.** Every campaign is a structured attempt to find the next crash before a user does. The program has already surfaced, clustered, and minimized 140 silent-NaN cases that would otherwise have been invisible.
- **Scope discipline.** No multi-OFE fuzzing will start until single-OFE closure criteria are met. That rule is enforced by the test runner, not by convention. The five remaining accepted-upstream slices are the explicit watchlist for the first multi-OFE pilot.
- **Evidence symmetry.** Every slice has the same artifacts an ablation incident has: deterministic reproducer, minimized input, patch lineage, regression test, and a closure-gate record. A reviewer can walk the entire campaign from raw classifier output to the final closure memo without trusting our summary of it.
- **Limits, stated openly.** Fuzzing cannot prove the model is bug-free. It can only prove the model survived the conditions we chose to press on. The stratification grid, the pressure profiles, and the oracle checks are all published so a reviewer can propose a new dimension to press on and reason about whether the current campaigns would catch it.

## Why you may see slightly different numbers

For the vast majority of simulations, outputs are unchanged. Where they do change, the pattern is consistent and explainable:

- **Boundary days, not whole runs.** Differences concentrate on specific days or events where the physics crossed a numerical edge case (near-dry channel, frost-layer transition, a zero-flow year in a dry-climate basin, a year in which a routing denominator collapsed). Annual and long-term totals typically shift by a very small fraction of a percent.
- **Short-term event peaks can differ more than long-term totals.** A single event on a boundary day can shift by a noticeable amount because the guarded code now reports a well-defined answer where the legacy code effectively reported an unconstrained one.
- **Rank-ordering of events can shift.** When two events are numerically very close, a tiny difference in the underlying arithmetic can flip their order. This is a known feature of any compiler migration; it is not a change in model skill.
- **Cross-compiler parity.** We compared the Linux build to the Intel IFX Windows build on the same staged watershed. Both completed cleanly with no crashes. Event-level values were not bitwise identical, but the long-horizon aggregate drift between the two was on the order of one part in a million. That is the level of agreement you should expect across well-behaved compiler targets today.

If you have a calibration or decision rule tied to a specific historical number, check it against the new output. In most cases nothing will need to change. In a small number of cases, a recalibration against the modernized baseline will give you a more defensible result than calibrating against values that depended on the old compiler's quirks.

## What this means for using WEPP going forward

- **Default baseline for legacy parity.** If your workflow does not need recent feature additions (e.g., `mofe`, road modules) or new output measures (e.g., `Qsnow`, `TSMF`), the binary `wepp_dcc52a6` continues to reproduce historical outputs bit-for-bit and is a valid choice for reproducing older studies.
- **Default for new work.** Use the date-versioned builds (`wepp_250915` and newer) for new runs. They are more stable, run on modern infrastructure, and carry the numerical guards described above.
- **When a release changes outputs.** We will publish, in plain language, what changed, why, which scenarios are likely to see differences, and whether recalibration should be considered. Each such change is backed by an ablation record that names the run, the simulation day, and the exact trigger so you can verify the attribution yourself.

## How we decide what to ship

Every fix in this brief went through the same discipline:

1. Start from a failing run on a specific binary.
2. Isolate the minimum input and the single line of code that flips it from failing to passing.
3. Apply the smallest possible guard at that exact location.
4. Confirm the full run completes and compare aggregate outputs against the legacy baseline.
5. Document the trigger, the fix, the residual risk, and the rollback plan.

We do not bundle unrelated changes, we do not silence the modern compiler's traps, and we do not accept a fix that changes physics we were not asked to change. The goal is the minimum set of changes that lets modern WEPP produce trustworthy results on modern hardware.

## Where to find the evidence

Each fix has a corresponding ablation record under [docs/ablation/](ablation/):

- [Numerical stability patches (newton, mann, hmax, wshchr)](ablation/20260414-numerical-stability-patches.md)
- [p325 SIGFPE — srivas42-claustrophobic-shortcut](ablation/20260418_p325_sigfpe_ablation.md)
- [pw0 SIGFPE — suppurative-skunk (watershed routing)](ablation/20260418_suppurative-skunk_pw0_sigfpe-wshdrv/incident.md)
- [pw0 SIGFPE — operational-berry (frost-layer indexing)](ablation/20260419_operational-berry_pw0_sigfpe-locate-frostn/incident.md)
- [pw0 SIGFPE — primitive-hug (frost-season soil-water arithmetic)](ablation/20260420_primitive-hug_pw0_sigfpe-saxfun-watdst/incident.md)
- [p14 SIGFPE — exorbitant-affidavit (hourly inter-layer seepage at an impermeable boundary)](ablation/20260420_exorbitant-affidavit_p14_sigfpe-perc-purk-watbal/incident.md)
- [p24 SIGFPE — srivas42-combatant-ionosphere (zero-duration runoff event in time-of-concentration)](ablation/20260421_srivas42-combatant-ionosphere_p24_sigfpe-wshpas/incident.md)
- [p258 + p1319 SIGFPE — twenty-two-fratricide / unveiled-grinder (watbal_hourly log10 domain)](ablation/20260425_p258-p1319_hillslope_sigfpe-watbal-log10/incident.md)
- [p1408 SIGFPE — taken-brainstem (watbal non-hourly log10 domain)](ablation/20260426_taken-brainstem_p1408_hillslope_sigfpe-watbal-log10/incident.md)
- [IFX vs Linux parity report](ablation/20260419_operational-berry_pw0_sigfpe-locate-frostn/20260420-ifx-linux-parity-report.md)
- [Ablation protocol](ablation/protocol.md) and [ablation standard](ablation/README.md)

Generative input fuzzing program (single-OFE tranche, Milestones 0–7):

- [Program overview and strategy](../generative-inputs-fuzzing/README.md)
- [Milestone 1 — wrapper property contracts](work-packages/20260421-generative-fuzzing-milestone1-wrapper-properties/package.md)
- [Milestone 2 — seeded soil/landuse generators](work-packages/20260421-generative-fuzzing-milestone2-seeded-soil-landuse-generators/package.md)
- [Milestone 3 — single-OFE stratified campaign](work-packages/20260421-generative-fuzzing-milestone3-single-ofe-stratified-campaign/package.md)
- [Milestone 4 — single-OFE boundary amplification](work-packages/20260421-generative-fuzzing-milestone4-single-ofe-boundary-amplification/package.md)
- [Milestone 5 — single-OFE sensitivity calibration](work-packages/20260421-generative-fuzzing-milestone5-single-ofe-sensitivity-calibration/package.md)
- [Milestone 6 — single-OFE boundary patch closure](work-packages/20260422-generative-fuzzing-milestone6-single-ofe-boundary-patch-closure/package.md)
- [Milestone 7 — single-OFE open-slice closure memo](work-packages/20260422-generative-fuzzing-milestone7-single-ofe-open-slice-closure/artifacts/closure_memo_contract.md)
- [Milestone 8 — P5 hydraulic ablation (negative-result closeout)](work-packages/20260422-generative-fuzzing-milestone8-p5-hydraulic-ablation/artifacts/closure_memo.md)

## Running log of stakeholder-visible changes

### 2026-04-14 — Baseline policy published
Established the working policy: keep the modern compiler's error-checking turned on during validation, fix exposed defects with the smallest possible changes, and document every change with reproducible evidence. Gives all teams one decision framework instead of ad-hoc fixes.

### 2026-04-19 — operational-berry frost-layer crash resolved
Captured a reproducible incident package for a watershed run that crashed every time in simulation year 24 during frost processing. Fixed with a narrow bounds guard in the soil-layer lookup. The full 45-year run now completes on the same inputs.

### 2026-04-20 — Cross-compiler evidence (IFX Windows vs Linux)
Ran the same staged watershed through the Intel IFX Windows build and the Linux build. Both completed cleanly. Event-level outputs differ in sparse, localized places; long-horizon aggregates agree to roughly one part in a million. This is the expected level of cross-compiler agreement and is now documented as the acceptance criterion for compiler migrations.

### 2026-04-20 — Release posture clarified
For stability-focused releases, we now ship when (a) the run completes safely on modern hardware and (b) aggregate behavior matches the legacy baseline within documented tolerances. Bit-for-bit identity across compilers is not required and is not achievable in general; this is acknowledged openly in release notes rather than hidden.

### 2026-04-20 — Guidance for winter/frost boundary conditions
Explicit guards were added around winter and frost-season layer lookups to prevent invalid math states. Core hydrology is preserved. Expect the model to handle these boundary days more gracefully, with the possibility of small event-level differences on the affected days — not wholesale changes to how the model represents winter processes.

### 2026-04-20 — Dry-watershed (desert) hardening for the `upstream-scheme` incident
A watershed run in a dry-climate basin (`upstream-scheme`) was crashing during simulation because an internal storm rise-time calculation divided zero by zero during no-flow years. A minimal guard now recognizes the zero-flow condition and sets the rise-time to zero, which is the physically correct answer when there is no watershed flow to route. The fix was validated through the standard ablation discipline: staged reproduction of the crash, observability showing both inputs at zero at the failure boundary, guard probe confirming the guarded branch activates on the same state, and full replay completing with the watershed success marker. The guarded binary (`wepp_260420`) has been vendored to production after all provenance gates passed.

### 2026-04-20 — Hillslope-binary hourly-seepage crash at an impermeable boundary
A hillslope run crashed reproducibly in its first simulation year inside the hourly water-balance update. The trap was isolated to the harmonic-mean conductivity expression that combines a soil layer with the layer immediately below it: when the lower layer's saturated conductivity is zero (the encoding for an effective bedrock or impermeable boundary), the harmonic mean is mathematically undefined. A one-line guard now sets the inter-layer seepage rate to zero in that condition — the physically correct answer when no water can pass downward — instead of evaluating the undefined expression. A sibling-arithmetic audit confirmed no other site in the same routine carries the same fault pattern. A broader screen of the run-archive flagged seven additional hillslopes in the same run that exhibited the identical chain; all eight resolve cleanly under the single guard. This is the first failure documented in this brief that lived in the hillslope binary rather than the watershed binary.

### 2026-04-20 — primitive-hug frost-season soil-water crash resolved
A second frost-season SIGFPE was reproduced on the `primitive-hug` watershed run, which crashed every time at simulation year 13 inside the soil-water-distribution helper called from winter processing. The trap was isolated to power and divide operations in `saxfun` acting on degenerate frost-layer inputs. A narrow domain-guard patch was added to that routine only — the soil-layer contract used by the rest of the model was left unchanged. The patched binary completed the full 14-year watershed run cleanly. This is a distinct incident from the operational-berry frost-layer fix even though both surface in the same winter call chain.

### 2026-04-20 — Closeout hardening for the dry-watershed fix
Four closeout deliverables accompanied the `wshpas` guard: (1) a compact standing regression that replays the original failing watershed and verifies both pre-guard failure and guarded success; (2) a five-watershed non-desert parity panel (humid warm, humid very wet, snow-dominant, seasonal marine, mixed mountain) where the guard never activated and outputs are byte-identical to the pre-guard modern build — confirming the fix is specific to the dry-flow condition and does not perturb wet-climate results; (3) a systematic audit of other division sites in the watershed routing code for the same fault pattern, with every candidate either already guarded or structurally not-at-risk; and (4) a tightened binary-provenance gate that automatically rejects builds linked against non-system loaders, non-system libraries, or Intel-compiler fingerprints before any binary can be vendored.

### 2026-04-21 — Zero-duration runoff event in the time-of-concentration calculation
A second guard was added to the same routine that hosted the dry-watershed fix, but at a completely different expression. A hillslope run was crashing on its very first routed runoff event because the recorded event duration was zero while the runoff volume was non-zero — a pairing that makes the per-event runoff intensity (volume divided by duration) mathematically undefined. The legacy compiler tolerated it; the modern build raised SIGFPE the moment the time-of-concentration formula evaluated the intensity term. A narrow guard now floors the duration term before the divide and substitutes the routine's already-existing zero-intensity sentinel. Three additional belt-and-suspenders guards were placed on arithmetically equivalent siblings in the same expression block (slope term, composite denominator, downstream zero-volume site); none of those three fired on the originating run, but they are recorded in the incident's sibling-arithmetic audit so the same fault pattern cannot recur silently. A control hillslope from the same run that did not exhibit the fault remains byte-identical to the pre-guard build, confirming the new guards do not perturb normal events.

### 2026-04-22 — P5 hydraulic ablation campaign closed with no patch (Milestone 8)
The three wet-climate P5 slope-response slices that exited Milestone 7 as `accepted_upstream` were the first to be promoted into a Fortran-side ablation campaign under the same protocol used for the thirteen fixes earlier in this brief. Four hypothesized mechanisms were tested, each in its own isolated lane against a matched 120-seed subset: the `route` routine's denominator boundary (`route.for`), the `irdgdx` denominator paths in `sloss.for`, the kinematic-wave slope-coupled arithmetic in `unifor.for`, and the Manning-path arithmetic in `mann.for`. Every behavioral lane returned the same non-pass count as the observability-only baseline, to the case. None of the four mechanisms attributed the failure, and per protocol all four candidate edits were rolled back rather than merged — the accepted patch set is empty. Two consecutive 200-case targeted reruns on each of the three slices confirmed the symptom remains deterministic and reproducible (non-pass in the 22–32 range on each rerun), so each slice retains its `accepted_upstream` status unchanged. A new lead surfaced during lane execution: a runtime-error signature repeatedly localizing to an end-of-file read path in `stmget.for` line 122, which is the first hypothesis for the next cycle.

Two caveats were recorded alongside the memo. First, the 1,008-case calibrated rerun of the post-M8 campaign (with all lanes rolled back, so functionally equivalent to the M7 post-patch code state) showed composite non-pass at 91 rather than the 41 reported after Milestone 7. The delta is not a regression introduced by M8 — no patches landed — but a campaign-to-campaign drift observation that tells us the closure gate itself needs explicit variance characterization before small absolute deltas can be attributed. The matched-seed lane design used inside M8 is specifically immune to this drift, and that is the gate the investigation relied on. Second, a binary-release risk distinct from the ablation work was captured in the same memo (the production `src/wepp` ELF loader target) so it is visible to release review.

No speculative patch landed. The discipline that refuses to merge a guard without measurable, matched-seed causal attribution is the same discipline that produced the thirteen trustworthy fixes earlier in this brief; the only difference is that in this cycle it ran in the direction of a negative result. A separate P2 event-edge and P4 texture/density ablation package is slated next.

### 2026-04-25 — Hourly water-balance hydraulic calibration crash resolved (hillslope binary)

Two hillslopes in separate watershed runs (`twenty-two-fratricide:p258`, `unveiled-grinder:p1319`) were crashing inside the hourly water-balance routine during hydraulic initialization. The observability lane localized the failure to `hk = -2.655 / alog10(fc/ul)`: when a soil layer has zero field capacity, the ratio evaluates to zero and `log10(0)` is undefined. A narrow guard now sets `hk = 0` when the ratio is non-positive — the bounded fallback for a degenerate layer — instead of evaluating the logarithm. Both incident seeds complete cleanly. A compiler-provenance issue was also surfaced and resolved: the prior release binary was linked against a Homebrew interpreter rather than the system loader; the fix was rebuilt and validated under the pinned system compiler, and a readelf gate now enforces this requirement before any binary can be vendored. Release targets are `wepp_260425` and `wepp_260425_hill`.

### 2026-04-26 — Non-hourly water-balance hydraulic calibration crash resolved (taken-brainstem:p1408)

The same `hk = -2.655 / alog10(fc/ul)` expression guarded in `watbal_hourly` by fix #12 was found unguarded in the non-hourly `watbal` path. The `taken-brainstem:p1408` hillslope — first reported failing on `wepp1` — reproduced deterministically on both the release binary (`wepp_260425_hill`) and the source build, with the trap address resolving to `watbal_` rather than `watbal_hourly_`. The observability lane confirmed `fc = 0`, `ul > 0`, ratio `0.0` at the failure boundary. The same guard pattern was applied: `hk` is set to zero when `fc/ul` is non-positive, instead of evaluating the undefined logarithm. Fuzzy regression across 11 hillslope seeds — including p258 and p1319 from fix #12 — introduced no regressions. This is the thirteenth Fortran-side guard and closes the known unguarded sibling of fix #12.

The release closeout for this incident also replaced the first `wepp_260426` artifacts with a rebuilt `wepp_260426`/`wepp_260426_hill` pair from the pinned system compiler (`/usr/bin/gfortran`) after the earlier cut was judged non-viable. Pre-vendor gates were rerun and passed on the replacement build: host smoke checks, permanent hillslope watchlist replay (including `p1408`, `p258`, and `p1319`), full pytest, reconciled-condenser watershed replay success marker, and ELF interpreter compatibility (`/lib64/ld-linux-x86-64.so.2`).

### 2026-04-22 — Generative input fuzzing program closeout (single-OFE tranche, Milestones 0–7)
The first full tranche of generative input fuzzing closed today. Across seven milestones, the program built a reproducible campaign pipeline — wrapper contract tests, seeded soil/management/climate generators, climate-by-slope stratified sampling, five mutation-pressure profiles, and an output oracle that flags silent `NaN`/`Inf` results even when a run exits cleanly — and then drove it at scale (1,008 cases per run) against the modern trap-enabled binary. Two independent guardrails enforce campaign validity on every run: a five-case positive-control set (all five must be detected as failures) and the per-case output oracle. The scaled campaigns surfaced 140 silent-NaN cases concentrated in nine priority slices; four of those slices were closed under the frozen two-rerun, two-hundred-case, zero-non-pass criterion, and five were classified as **accepted upstream** — reproducer preserved, patch attempt reduced the symptom materially, residual failures promoted into the Fortran-side ablation track rather than papered over with a broader input clamp. Net effect on the full calibrated rerun: composite non-pass dropped from 134 to 41 (a 70 percent reduction) with the sensitivity gate still passing 5/5. All patches landed in the input-generation layer, not in the WEPP binary, and carry dedicated regression tests. Multi-OFE fuzzing is gated on this tranche's closure memo and will begin with the five accepted-upstream slices as explicit watchlist items.

## Bottom line

The model you know is the same model. It is now compiled with a modern, stricter toolchain that catches a small number of long-standing numerical edge cases the old compiler ignored. We have fixed those cases with the narrowest defensible changes, evidence-backed and reversible. You should see fewer mysterious run failures, the same physics, and — in a small and well-characterized set of boundary situations — slightly different numbers than the old binary produced. The legacy binary remains available for historical reproducibility when that matters for a specific study.
