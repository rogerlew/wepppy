# MC candidate execution gate and retained-state risk

Date: 2026-10-21. Independent secondary QA, read-only production investigation.

## Gate disposition

The required native suite **fails** for explicit candidate
`mc-interface-candidate-v2/src/wepp`: 409 passed, one failed, two existing tarfile
warnings, 938.70 seconds. The upstream-scheme 100-year watershed regression
raises `subprocess.TimeoutExpired` at its existing 900-second limit; the
subprocess is killed with return code -9. Promotion and commit remain blocked.
Increasing the timeout alone would not resolve the state risk described below.
That broad run used the earlier portable-test set; the expanded 55 interface
tests pass separately and cannot supersede this failed executable gate.

The run was progressing, not deadlocked. Its final observer record is simulation
year 16, day 81, channel 20. A live observation near termination showed elapsed
and CPU time both 14:29, at 99.9% CPU. This differs materially from the previous
guard candidate's successful full-suite gate of 567.32 seconds. The earlier
bounded source/publication and portable-test reviews remain valid within their
scope; they do not override this failed execution gate.

Candidate WSHCHR SHA256:
`a1256946fba32df368db16bb2dc051bfaf78667d9d2c56d4c010e68717265dff`.
Evidence is retained under
`/workdir/watershed-physical-water-repair-20261021/mc-interface-runtime-qa-v1/`:
the complete pytest failure, bounded terminal observer excerpt, binary/source
hashes and `receipt.json`. No failed outputs are treated as a completed run.
Receipt SHA256:
`adcdc95d74f86e6150d3c50855c8fffcfcdfe7933f008211ee3c4ec5c7f6f89c`.

## Independent recurrence derivation

WSHCHR selects reference discharge before CHRSTATE restores the retained interior
profile. In MC4, `qref <= eps` gives `K=tk=0` and `X=cx=0`; the resulting
coefficients are `c1=c2=1`, `c3=-1` in exact arithmetic. Under zero boundary and
lateral forcing, the recurrence becomes

```text
q[j,n] = q[j-1,n] + q[j-1,n-1] - q[j,n-1]
q[0,n] = 0
```

Induction over segments gives `q[j,n] = -q[j,n-1]`: the interior profile changes
sign without transporting or decaying. An even number of time steps returns
the identical profile at midnight. The `any(qs(...).ne.0.)` guard keeps invoking
this recurrence indefinitely whenever that retained state is nonzero. The guard
correctly prevents loss of interior water, but is not sufficient to ensure that
the selected coefficients describe its continued routing.

The actual failed trace repeatedly reports zero qref and zero reference celerity.
The grid path substitutes dx=1 and frequently reaches the 101-segment cap; its
terminal record uses 101 segments over roughly 1264.3 m. This establishes the
zero-reference branch and large grid, not the profile magnitude or time spent
inside that branch: ordinary observer records do not contain the needed interior
state or coefficient counters. Denormal arithmetic is a plausible additional
cost, not a demonstrated cause of this fixture's timeout.

The fixture has no `chan.inp`. WSHINP's default lower time-step bound is 60 seconds
(1440 steps/day), materially denser than the 600-second portable probes. Any
candidate recurrence correction must be tested at this actual gate resolution.

## Reference experiment and bounded acceptance controls

The science reviewer's isolated `reviewer-reference-v1` experiment routes an
actual late-day 100 m³ pulse through WSHCQI/WSHCHR. Its baseline MC4 recession
uses zero reference, changes to 101 segments and exports zero. Reusing the
previous positive reference retains 58 segments and exports about 99.999885 m³;
using half the positive interior maximum exports about 100.323324 m³ with a
different coefficient-coordinate revaluation. These are experiment observations,
not acceptance of a new production policy or full hydrology closure.

Reusing the previous valid MC4 reference is the narrower trial: it retains the
parameterization that produced the state instead of deriving another amplitude
rule from that state. A production choice still requires the scientific contract,
appropriate ADR, isolated comparison and gate completion. Keep it scoped to MC4
unless changes to KW3/MC5 are independently justified. Any saved reference must
be per channel and reset with the same new-simulation condition as CHRSTATE.

Minimum controls before promotion of a bounded correction:

- A dry day, late positive pulse, and multiple subsequent dry days using actual
  state retention. Observe reference, grid, raw profile, accepted outlet,
  coefficients and publication; demonstrate removal of the K=0 sign cycle.
- Current reference equal to zero and small positive reference at/below the
  existing epsilon. The degenerate branch is `<= eps`, not only exact zero.
  Include weak retained state and the absence of a prior valid reference so an
  unhandled case cannot silently appear repaired.
- Normal and subnormal retained magnitudes, with executed-cell counts and bounded
  runtime evidence. Natural roundoff decay must be observed; do not assume that
  all subnormal states eventually round to zero or erase them without accounting.
- All-zero state, ordinary positive-reference trajectories, MC5 and KW3 controls,
  plus channel isolation and new-simulation resets. Include both even and odd
  interval counts so an even-day sign cycle cannot masquerade as stable state.
- The unchanged 900-second upstream-scheme fixture gate against the exact fresh
  candidate, followed by the required native gates and affected replay evidence.

These controls concern a demonstrated recurrence/reference boundary. They do
not expand this review into a requirement to finish unrelated signed-exchange
or general clipping repair. No production source edits were made here.

## Follow-up: exact timeout regression passes for v5

The original v2 failure above remains historical evidence. The exact previously
failing 100-year fixture now passes against `mc-reference-candidate-v5` without
changing its 900-second timeout: two passed, two existing tarfile warnings,
580.64 seconds, with final year 100/day 365/channel 31 observed. The retained
log is `mc-reference-v5-failed-gate-retest.log` under the external evidence root.
The bounded reference and exact fixed-point source/test review is recorded in
[mc-reference-qa-review.md](mc-reference-qa-review.md). Full native-suite
completion remains pending at this checkpoint; this retest does not close
signed-exchange or clipping acceptance.
