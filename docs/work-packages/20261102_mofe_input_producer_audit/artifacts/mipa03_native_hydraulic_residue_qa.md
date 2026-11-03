# MIPA-03 independent hydraulic, residue and initialization QA

Reviewer: `mipa03_native_qa`, 2026-11-03 UTC. **PASS for the bounded actual
consumer comparisons below.** This does not establish whole-model histories,
final release binaries, report readback or configured service execution.

## Method and reference binding

Native `tests/test_specialized_rap_hydraulics.py` uses the separately SHA-bound
`tests/fixtures/specialized_rap_hydraulic_reference` snapshot from model source
`2e5928702edd5526a119216bd6be5997729ec72e`. Its original INFPar, DECOMP, INITGR,
PTGRP and structure include are unmodified. Initialization uses the previously
bound growth fixture's remaining original includes; candidate compilation uses
current sources with supported hill includes. All probes compile in private
folders; no shared build, production source or installed binary is modified.

Tests compile the actual INFPar source span beginning with the existing
`avsat >= avpor*avcpm` adjustment through final conductivity assignment. A single
observation assignment captures the actual power result immediately before the
actual lower-limit branch. Python supplies inputs and compares printed values;
it does not compute expected hydraulic formulas. Both programs emit the actual
saturation, limits, ground cover, `kfs`, `kus`, power result, final `keff`, `ks`,
first three layer conductivities, `dtheta` and `sm` for 12 distinct OFEs.

DECOMP tests compile the actual fire-residue block. INITGR is compiled whole,
with no cover arrays allocated beforehand, exercising its pre-reader state use.
PTGRP tests compile its actual cutting LAI/heat-unit block. These are bounded
consumer tests, not replacements for complete parent routine control flow.

Compiler: system gfortran with `-O2 -fcheck=all -finit-local-zero
-ffpe-trap=invalid,zero,overflow -ffp-contract=off`; COMMON-based initialization
also uses `-fno-align-commons -mcmodel=medium`. Candidate observer calls link the
actual `rap_state` module, with observation off. No stub suppresses those calls.

## Results

Commands from the selected native checkout:

```sh
PATH=/usr/bin:/bin:$PATH pytest tests/test_specialized_rap_hydraulics.py -x -q
PATH=/usr/bin:/bin:$PATH pytest tests/test_specialized_rap_growth.py tests/test_specialized_rap_hydraulics.py -x -q
```

Observed hydraulic/residue/initialization result: **226 passed in 4.02 seconds**.
Current-source combined result: **295 passed in 7.38 seconds**. The combined run
rebuilds both consumer programs after addition of the optional native observers;
its 69 growth cases overlap the earlier growth report and must not be summed twice.

The new checks include:

- 200 exact-byte conductivity comparisons: five burn classes/boundaries, four
  cover values, five saturation states and adjustment on/off, each across 12 OFEs;
- direct confirmation of the preceding .99 saturation cap followed by the
  reference's additional .99 factor, producing approximately .9801;
- actual ground-cover-floor equivalence, distinct OFE `kfs`, and execution of
  both the raw-power and lower-limit branches;
- equality of `ks`, `ssc(1)` and `ssc(2)` only with adjustment enabled, while
  the third layer retains its own prior conductivity;
- 16 exact-byte residue comparisons with activation on/off, observed/transformed
  modes, fire-eve/fire-day/fire-next-day and following-year anniversary;
- no transform dependence in the exact fire-day residue event; class-specific
  burned OFEs change, unrelated classes remain unchanged, and following-year
  anniversary does not repeat the exact-date event;
- four whole-INITGR comparisons covering annual/perennial and senescence flags,
  with matching biomass/height/LAI/heat units and zeroed `ccmxfr`;
- two cutting LAI/heat-unit comparisons, preserving distinct OFEs 2 and 10; and
- immutable reference fixture hash verification.

These reproduce reference semantics, including scientifically unusual behaviors.
They do not convert reference preservation into calibration or general correctness.

## Retained attempts and limits

Evidence root:
`/wc1/holdouts/mipa-native-r7-20261103/hydraulic-residue-qa`.
It retains v1–v4 logs, `combined-v5.log`, all compiled probe directories and
`manifest.json`. The first attempt used an extraction terminator not retained
in the candidate; it failed before comparison. The third attempt coincided with
addition of `rap_trace` and failed linking the newly called module procedure.
The extractor now uses the shared following section marker and the candidate
links the actual observer module. Both failures remain retained; neither is a
model discrepancy or a successful gate.

INFPar evidence covers its actual final 9005 consumer sequence, not upstream
soil averaging or the complete generic/RAP effective-K bypass. DECOMP evidence
covers the actual burn block, not all decomposition/cover redistribution before
and after it. INITGR and cutting probes do not exercise the full PTGRP management
state machine or every reset call. Dynamic full histories, observer neutrality,
ordinary-mode controls, exact final binaries and configured artifact propagation
remain parent acceptance requirements. No broad release claim is made here.
