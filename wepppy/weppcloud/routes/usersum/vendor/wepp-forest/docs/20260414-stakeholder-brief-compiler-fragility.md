# Stakeholder Brief: Compiler Fragility, Result Confidence, and the Path Forward

Date: 2026-04-14  
Audience: Product owners, program managers, support leads, and model users

## Executive Summary

WEPP is a long-lived scientific model with legacy code paths that were historically executed under a narrow compiler/toolchain environment.  
When we change compilers or runtime settings, we are not "changing science" arbitrarily; we are exposing hidden assumptions that were previously masked.

This creates a hard reality:
- Some historical outputs were consistent because the old toolchain was forgiving, not because every path was correct.
- Some user workflows may have been calibrated to those legacy quirks.
- Preserving trust now requires fail-fast behavior, strong observability, and controlled ablation-based change management.

## Why This Is Happening Now

Over many years, the model accumulated technical debt that was not fully covered by automated regression tests and contract checks.

Historically, the old Intel `ifort` environment often acted like a "reality distortion field" by tolerating or masking fragile program behavior, for example:
- local memory appearing zero-initialized when code did not explicitly initialize it,
- local state persisting between calls when code relied on implicit static behavior,
- floating-point edge cases not trapping immediately,
- compiler/runtime choices silently steering execution around unstable branches.

When moving to newer toolchains, these hidden assumptions surface as:
- floating-point traps,
- stalls/non-termination,
- path divergence at condition boundaries,
- changed outputs even when source edits are minimal.

### Cross-Compiler Gotchas in Plain Language

These are not abstract compiler trivia. They are concrete ways a legacy numerical codebase can behave differently even when the scientific equations were not intentionally changed.

| Gotcha | What it means in practice | Typical symptom |
| --- | --- | --- |
| Accidental zero-start behavior | A routine forgets to initialize a local scalar or work array. One compiler/runtime may happen to present zeros on entry, while another exposes leftover stack data. | Different first-event behavior, unstable counters/flags, or output drift that looks random but is actually implementation-dependent. |
| Accidental "sticky" local state | A routine implicitly depends on a local variable behaving as if it were `SAVE`d between calls. A different compiler/storage model may reset that state, reuse old memory differently, or reorder where it lives. | Different solver history, changed event sequencing, or results that depend on call order rather than model intent. |
| Silent arithmetic versus fail-fast traps | One toolchain may let divide-by-zero, overflow, underflow, or invalid operations continue long enough to produce plausible-looking outputs or delayed corruption. Another traps immediately. | A legacy run "finishes" but carries hidden bad state, while a newer run fails early and points closer to the real defect. |
| Floating-point model and convergence sensitivity | Small differences in rounding, denormal handling, optimization, or IEEE behavior can change whether an iterative numerical loop converges. | One compiler completes while another stalls or spins. A documented example in this repo is the Hangman Creek case, where the `ifx` build hung in erosion routing for a narrow wet-soil scenario that the `gfortran` build completed. |
| Threshold-driven branch divergence | Tiny numeric differences at a comparison boundary can send execution down a different branch, for example at tolerance checks, rain/snow partition logic, or routing thresholds. | Two runs with the same inputs both complete, but they follow different paths and diverge in outputs even though the source edit was minimal or nonexistent. |

## Why "Old Results" Are Not Automatically "Correct Results"

Historical consistency is important, but it is not proof of correctness.

Legacy results can be systematically biased by:
- undefined or implementation-dependent behavior,
- silent arithmetic exceptions,
- uninitialized-state dependence,
- branch decisions altered by tiny floating-point differences.

In plain terms: the old toolchain could produce repeatable numbers that were partly artifacts of legacy execution behavior.  
Those numbers may be operationally familiar, but familiarity alone is not scientific validity.

## Calibration Risk: A Critical Stakeholder Point

Users may have calibrated workflows to match historical outputs.  
That means a "fix" can look like a regression from the user perspective even when it removes silent model error.

This is expected in mature modeling programs and must be managed explicitly:
- distinguish **numerical bug fixes** from **intended scientific model changes**,
- preserve reproducible baselines for comparison,
- document when and why outputs shift,
- provide migration guidance for recalibration when needed.

## Current Reality: A Legacy Rube Goldberg Effect

The model behaves like a tightly coupled legacy machine: small runtime/compiler differences can trigger downstream behavior changes in non-obvious ways.

This is not a reason to freeze progress.  
It is a reason to use strict operational discipline when changing anything in numerical paths.

## Recommended Operating Policy

### Version Scope and Default Recommendation

This policy applies to the date-versioned executable line starting at `wepp_250915` and newer.

For users who do not need newer capabilities, the recommended stability baseline is `wepp_dcc52a6`.

Use `wepp_dcc52a6` when you do not require:
- newer feature paths (for example `mofe`, roads), or
- newer output measures (for example `Qsnow`, `TSMF`).

Use date-versioned builds (`wepp_250915` and later) when those features/outputs are required, with ablation-based validation as the default control process.

### 1) Keep floating-point traps enabled in validation lanes

Rationale:
- traps convert silent corruption into explicit, localizable failures,
- they shorten time-to-root-cause,
- they prevent hidden bad states from propagating into "plausible but wrong" outputs.

### 2) Treat fail-fast as a quality feature, not a regression

Explicit early failure on invalid states (for example divide-by-zero conditions) is safer than silent continuation.

### 3) Use ablation as the default incident-response method

Ablation testing means we change one thing at a time and observe the effect.

In plain terms:
- start from a known baseline run,
- make one small change,
- rerun the same input,
- compare results,
- keep the change only if it clearly improves stability/correctness,
- roll it back if it has no effect or causes unwanted side effects.

Why this matters for stakeholders:
- it avoids guesswork,
- it prevents "bundle changes" that hide root causes,
- it reduces regression risk,
- it gives clear evidence for every keep/rollback decision.

Reference protocol: `docs/ablation/protocol.md`.

### 4) Separate "parity" from "correctness" in release decisions

- **Parity**: how close new outputs are to historical outputs.
- **Correctness**: whether execution avoids undefined/invalid behavior and honors model contracts.

Both matter, but parity should not force retention of known-invalid execution paths.

### 5) Maintain transparent decision records

For each incident/fix set:
- baseline signature,
- hypothesis,
- ablation evidence,
- keep/rollback decision,
- residual risk statement.

Reference example incident record: `docs/ablation/20260414-numerical-stability-patches.md`.

## What Stakeholders Should Expect

Short term:
- More explicit run failures where legacy runs may have "completed."
- More diagnostic output and stability-focused patch notes.
- Occasional output shifts tied to documented defect removal.

Medium term:
- Fewer opaque failures,
- faster root-cause isolation,
- stronger reproducibility across environments,
- increasing confidence that outputs reflect model logic rather than compiler accidents.

## Suggested Communication Standard for User-Facing Changes

For any release that can affect outputs, publish:
- what changed (plain language),
- why it changed (defect, guardrail, or scientific update),
- expected impact scope (which scenarios are likely affected),
- whether recalibration may be needed,
- where to find evidence (ablation summary + comparison artifacts).

## Bottom Line

The safest path forward is exactly the current strategy:
- keep FP traps in validation,
- expose and fix technical debt as encountered,
- apply conservative, evidence-based ablation,
- ship only minimal, justified patch sets.

This protects user trust better than preserving legacy behavior that may be stable but undefined.
