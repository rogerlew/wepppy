# MC-preserving continuity audit

Status: local implementation findings, not complete watershed closure.
The operator explicitly retained Muskingum-Cunge dynamics and rejected replacing
its storage authority with geometric volume. See ADR-0101 and
[scientific review](mc-continuity-review.md).

## What the recurrence establishes

For one segment and time interval, use the actual native K, X and lateral mean:

    F = dt/2 * (I_old + I_new - O_old - O_new) + dt*dx*lateral_mean
    M = K * [X*(I_new-I_old) + (1-X)*(O_new-O_old)]

The native recurrence implies F=M within coefficient and arithmetic precision.
For fixed K/X, M is the change in algebraic storage H=K[X*I+(1-X)*O].
When coefficients vary, define C=H(new coefficients, old discharge) minus
H(old coefficients, old discharge). Then M=H_new-H_old-C. C is parameter
revaluation, not an observed physical source or an authorized correction flux.
Daily grid/boundary changes add another explicitly measured jump.

The portable tool `tools/mc_continuity_probe.py` executes 16 actual native
controls: MC4/MC5, point/interval lateral modes, adaptive versus fixed grid and
reference discharge, and side/top input. Each runs three complete days: steady
flow, a late positive pulse, then recession. It observes all segment/time updates,
K/X and recurrence coefficients, full initial/final nodes, boundary rates and
publication. The fixed lane freezes both eight segments and qref=0.5; it is not
an isolated test of grid selection alone.

Independent off/on checks preserve all 16 outlet trajectories and publication
records exactly. Parser checks reject missing/duplicate/reordered steps, missing
boundary/node records, nonfinite values and duplicate publication. Day blocks
are sorted before transition calculations. The telescoping endpoint identity is
bookkeeping, not independent evidence of completeness or water conservation.

## Confirmed publication and downstream disagreement

`tools/mc_cascade_probe.py` uses actual WSHCHR for both channels and actual
WSHCQI for the downstream daily-volume intake. The first channel writes tmpvol
itself. No surrogate transfer equation replaces those calls.

For every tested transfer, upstream publication equals downstream daily intake,
and the upstream rate integral equals downstream rate intake. But those two
representations disagree with each other. In point mode on pulse day:

| Method | Source placement | Downstream daily volume minus rate-integrated input |
| --- | --- | ---: |
| MC4 | Side | +1,363.206 m³ |
| MC4 | Top | -1,558.219 m³ |
| MC5 | Side | +1,653.886 m³ |
| MC5 | Top | -1,545.950 m³ |

These are controlled interface discrepancies, not measurements of water created
by MC. The source pulse also has a known 300 m³ rectangular/trapezoidal boundary
difference; retain it separately rather than attributing everything to storage.

The source path is explicit: WSHCHR computes chvol using daily volint and its
reported storage change, then sets runvol/tmpvol. WSHCQI includes tmpvol in
rvotop. Separately, downstream WSHCHR sums upstream q1 arrays into qin. MC dynamics
can be internally consistent while those two downstream input representations
remain inconsistent. Fixing this requires reconciling source integration and
published/accepted transfers, not replacing MC with geometric storage.

## Coefficient and grid transitions

MC4 coefficients are fixed within each diagnostic day. MC5 changes them within
the recurrence. Endpoint algebraic storage without the coefficient revaluation
term therefore does not measure the MC5 continuity increment.

For MC4 adaptive side input, the second-day combined jump is -464.407 m³.
A declared diagnostic decomposition holds prior K per unit length and X while
mapping the old profile, then replaces the boundary, then changes coefficients:
about +11.608 m³ comes from grid representation and -476.015 m³ from coefficient
revaluation; remap rounding is about -0.000001 m³. For top input the -1,171.107 m³
jump is entirely coefficient revaluation in this control. The frozen grid/reference
controls have zero jumps. This is an attribution convention, not a new remapping
or storage-authority contract. Variable spatial MC5 transitions remain combined.

## Additional implementation defect: skipping live interior state

The MC execution guard checks only inlet/outlet and lateral forcing. With dry
boundaries and a nonzero retained interior profile, it skips every recurrence
update and leaves the initialized zero state array in place.

A fixed-grid, positive-coefficient MC4 control begins with one interior node at
1 m³/s and all other nodes/boundaries zero. Its MC algebraic inventory is
1,262.180542 m³. The original guard exports zero and clears the profile. The
minimal correction also checks whether any previous interior node is nonzero;
the unchanged recurrence exports 1,262.179855 m³, leaving negligible state. The
0.000687 m³ difference includes native rounding and tiny outlet clipping.

Six native regressions (MC4/MC5, three pulse positions) fail before the change;
two all-zero controls pass. All eight pass with the correction. This demonstrates
an admissible-state defect, not how often existing project runs encounter it.
No coefficient formula, Manning relation, clipping rule or storage definition
changes. The existing all-zero fast path remains.

## Remaining repair boundaries

- Reconcile source cell volumes with actual top and lateral solver quadrature,
  including time-zero carry and events crossing midnight.
- Represent channel-local sources, signed exchanges and deferred baseflow exactly
  once, preserving their timing and the channel-soil coupling.
- Make accepted exported rates and downstream daily transfer volumes agree.
  Do not accomplish this by inventing a physical store from a balance residual.
- Keep coefficient/grid changes, skipped-state behavior and clipping explicit.
  Algebraic storage positivity and geometric equality are not imposed MC gates.

The source guard is a separately validated correction. It does not resolve the
publication mismatch or the four expected-failure channel-local tests. No release,
vendoring, deployment or change to the dated 261021 comparator is authorized here.
