# Stakeholder Brief: Modernizing the WEPP Build — What Changed, Why, and What to Expect

Date: 2026-04-14 (revised 2026-04-20)
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

### 11. Built-in observability for future incidents

We added an optional, off-by-default diagnostic log that records exactly which phase of the simulation was executing when a run fails. This is how we were able to localize the fixes above to specific channel elements, hillslopes, days, and years within long simulations. It has no effect on results when it is off.

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
- [IFX vs Linux parity report](ablation/20260419_operational-berry_pw0_sigfpe-locate-frostn/20260420-ifx-linux-parity-report.md)
- [Ablation protocol](ablation/protocol.md) and [ablation standard](ablation/README.md)

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

## Bottom line

The model you know is the same model. It is now compiled with a modern, stricter toolchain that catches a small number of long-standing numerical edge cases the old compiler ignored. We have fixed those cases with the narrowest defensible changes, evidence-backed and reversible. You should see fewer mysterious run failures, the same physics, and — in a small and well-characterized set of boundary situations — slightly different numbers than the old binary produced. The legacy binary remains available for historical reproducibility when that matters for a specific study.
