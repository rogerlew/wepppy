# Disposition: raw versus clipped transport-capacity deposition

Status: **confirmed source-level inconsistency for a varying negative raw polynomial; generated-run exposure and physical-domain prevalence remain undetermined.** It is not demonstrated to be a new U11 regression. Do not label all such inputs unsupported, infer production prevalence, or expand the solver before the targeted observation below.

## What is confirmed

The actual ROUTE chain reproducer `/tmp/route-u11-clipped-polynomial-probe.py` was independently executed. With raw C=-.001+.1*x, incoming L=.01,q=.1,phi2,theta=D0, the raw polynomial is negative until approximatelyx=.01. Shared DEPCAP reconstructs C_clip=max(C_raw,0), while DEPEQS's analytic rate equation still uses the raw polynomial derivative. At the first grid point native L=.007352616172283888, versus the zero-capacity ODE reference .008264462809917355.

This is an11.0333% spurious sink in that synthetic caller fixture, not a printing-roundoff discrepancy. Using nominal exact inputs, the extra sink is-.0009118457300275482, predicting native L=.007352617079889807; retained float32 input arithmetic explains the remaining small difference.

The inconsistency can be derived without assuming a new physical law. Let v=x+q, D be deposition rate, and R the raw capacity polynomial. DEPEQS solves:

`D' + (1+phi)*D/v = phi*(R'-theta)/v`.

DEPOS reconstructs `L=C-D*v/phi`, where `C=max(R,0)`. Differentiation gives the implemented load equation:

`L' = phi*(C-L)/v + theta + (C'-R')`.

Where R<0, the extra forcing is `-R'`. A rising negative raw polynomial creates an artificial sink; a falling negative polynomial creates an artificial source. A constant negative polynomial has R'=0 and, after the U10 boundary correction, does not by itself demonstrate this defect. Observer counts must distinguish these cases.

This is therefore more precise than an unspecified “model gap”: the source applies two incompatible representations within one deposition evolution. It becomes a confirmed error on valid generated inputs if observation finds varying-negative capacity on an actual wet DEPOS interval. Until then, retain it as an unresolved domain/representation gap rather than asserting a release-wide physical failure or waiving it.

## Why producer provenance matters

`src/profil.for:56` creates a linear normalized slope `s(x)=a*x+b` between input slope points. The unadjusted XINFLO capacity factors as a positive scale times `s(x)*(x+q)/(1+q)` (or the Case4 denominator q). With nonnegative slope and a valid wet interval, this normally remains nonnegative.

PARAM's OFE-continuity adjustment (`src/param.for:287` through367) replaces q by transport ratio r=tcrati and again constructs coefficients proportional to `s(x)*(x+r)/(1+r)`. With positive intermediate products and exact arithmetic, r is positive or less than-1, preserving nonnegativity on0<=x<=1. Thus arbitrary negative polynomials in direct caller tests are not automatically representative of generated Roads runs.

However, a concrete arithmetic route to generated negative coefficients exists and needs observation: REAL `tprod=(tterm1*tterm2)-1` can round to exactly-1 when the positive product is very small. Then tcrati=-1 and denominator0 is replaced with **positive**.001 by the existing guard. For positive slopes, `(x-1)/.001` is negative overx<1. This is a possible producer path, not evidence that it occurred in any validation run. Negative input slopes or coefficient cancellation are separate provenance possibilities.

## Minimum observation, no behavior changes

1. Observe each actual DEPOS call, not every negative coefficient or every EROD step. Intersect `[xb,xe]` with its strict wet support; require positive interval length. Evaluate the raw polynomial with retained REAL coefficients in double arithmetic. Check endpoints and the interior quadratic vertex; use polynomial roots to identify negative-support pieces and their lengths. This catches an interior negative dip missed by endpoint-only checks.
2. Retain a per-run count of all DEPOS calls, negative-support calls, and varying-negative-support calls, plus the first/worst exact records. A zero-exposure result needs complete call coverage, not merely no matching log lines.
3. Each positive record needs run/input/binary/source hashes, date/event and OFE/segment identity, xb/xe, actual incoming load, DU, qostar,phi,theta,ktrato and raw a/b/c; also roots, minimum raw capacity and its coordinate, negative-support length and raw derivative/variation. Preserve both raw and clipped boundary capacities.
4. For a positive exposure, replay only the smallest affected case with observation at PARAM/XINFLO to identify source coefficients, normalized slope, tterm1,tterm2,tprod,tcrati and actual denominator/guard branch. Capture existing native sediment scaling needed to express a load-error bound in kg. This separates a real producer defect from an unsupported externally supplied polynomial.
5. The observer binary must retain the production candidate's arithmetic and output hashes on controls and positive replays. Keep observer output separate, preserve exact input hashes, and verify complete simulated-year/event support. Run coverage across the U11 Roads840, downstream348, Disturbed and Cedar domains; seed-only non-exposure is insufficient.

The minimum first pass is the DEPOS observer only; extra producer instrumentation is needed only for a captured negative varying interval. No integrator or clipping behavior should be changed as part of observation.

## Bound and promotion implications

For a physical wet deposition interval, lambda=phi/(x+q)>0. The response to the extra forcing is attenuated, giving the rigorous local bound:

`abs(delta L) <= integral over negative support abs(R') dx`.

This is simply the raw polynomial's total variation on those pieces, computable from endpoints and vertices. Constant negative capacity has bound0. It permits a retained, physically scaled assessment of tiny exposures without fitting tolerances. An actual replay against an independent clipped-ODE reference is preferable when the bound is material or inconclusive.

- Complete observed non-exposure supports the statement “not exercised in the validated domains”; it does not prove global impossibility. Retain the reproducer and explicit domain limitation.
- Exposure only to constant negative capacity does not establish an error from this derivative mismatch.
- Varying negative exposure on generated valid inputs, with an unexplained mass effect above the frozen accounting/printing bounds, blocks promotion and triggers a bounded producer/consumer ablation.
- An ambiguous bound or unknown provenance is not a passing gate. Do not silently classify it as rounding or unsupported.

No production solver change is proposed here. Finish the frozen broad output gates and the targeted observation before deciding the smallest justified next action.

## Subsequent real-run evidence

The generated-domain uncertainty above is now resolved for specific U11 events: five exact-parity observation replays contain130 negative wet DEPOS calls, including materially large polynomials from PARAM's rounded ratio=-1/positive-zero-denominator guard. See `/tmp/param-denominator-sign-science-review.md` for verified seeds, sign derivation, shared shear/transport preconditions and the minimum remaining observation. This does not imply all130 calls are materially erroneous or establish unmeasured prevalence.
