# Independent PARAM U12 implementation review

Reviewed proposed `param.for` SHA-256
`889a0557fc43778097377165394bd6b10e0f7eb8d1cef96b849b516d651d262f`.
No production source edits were made by this review.

## Source scope and tests

No blocking implementation finding in the two exact-zero sign changes.
For positive physical continuity quantity t, ratio=1/(t-1) gives
ratio+1=t/(t-1), which approaches zero from below as t approaches zero from
above. Selecting -0.001 when that negative denominator rounds to zero and the
first slope is nonnegative preserves that side. Negative first slopes and every
nonzero denominator retain the previous branch. The existing denominator floor
is unchanged; sign correctness is not proof of exact continuity magnitude.

The normal producer prerequisites and fallback remain relevant. PARAM's normal
branch requires positive previous shear support and positive physical ratios;
the observed operands satisfy those conditions. XINFLO already moves qostar=-1
to -1.001 when qout>0, so the inherited QOSTAR fallback normally cannot introduce
this exact-zero denominator. The proposed code does not redesign that fallback.

Independently verified the original 10 tests at -O0 and -O2; additionally checked
27 exact parsed-coefficient parity controls spanning nonzero denominator
neighbors, both slope signs, and the actual extracted fallback. The expanded
15-test suite also includes ordinary positive producer ratios and fallback.
Probe: `/tmp/param-u12-review-probe.py`.

These tests execute extracted actual PARAM producer/guard statements, not the
entire PARAM call lifecycle. The independent shear/transport/combined full-run
lanes and generated particle/flux artifacts remain the decisive integration
checks. Do not label the scalar tests full-model acceptance.

## U12 residual terminal-support analysis

Independently reconstructed all **88** `NC_DEP` observations from the four
exact-parity U12 observer runs, restoring each nine-digit coefficient to its
exact float32 value and solving roots with 80-digit Decimal arithmetic.

- 31 ordinary, 44 DEPEND-failure seed, 8 buffer controls, 5 buffer-cap cases.
- Every negative region is a monotone terminal sliver ending at x=-qostar,
  with negative phi and negative qostar. This matches the finite-precision
  Case-4 polynomial, whose factored construction vanishes at that flow endpoint.
- **85/88** have no representable strictly-wet coordinate in the negative band.
- **3/88** have exactly one: the float32 coordinate immediately before -qostar.
- Maximum negative-band width: **2.01239379e-8** nondimensional distance.
- Maximum absolute negative capacity at a representable wet coordinate,
  including ktrato: **4.40624319e-8**.
- Maximum continuous terminal capacity defect: **1.68041837e-7**.

The three representable cases are ordinary 2007/day201/OFE3, DEPEND seed
2001/day120/OFE3, and DEPEND seed 2002/day313/OFE3. Therefore it is incorrect to
say all negative capacity is strictly outside native wet support.

Evidence and reproducible calculations:

- `/tmp/param-u12-terminal-support.py`
- `/tmp/param-u12-terminal-support.json` (all 88 cases, trace hashes, exact roots,
  negative-coordinate inventory and bounds)
- `/tmp/param-u12-terminal-weighted.py`

## Bound on the residual raw-versus-clipped equation discrepancy

Let Craw include ktrato, Cclip=max(0,Craw), and let E be the difference between
load reconstructed from Cclip with the raw-polynomial rate and the load from a
consistent clipped-capacity ODE, with equal load before the negative sliver.
On the strictly-wet negative-flow interval:

    E' + [phi/(x+qostar)] E = Cclip' - Craw'.

The coefficient phi/(x+qostar) is positive. Its integrating-factor kernel is
therefore at most one, giving the conservative, non-fitted bound:

    |E(x)| <= integral(root..x) |Craw'(s)| ds
           <= -Craw(-qostar).

All reconstructed slivers are monotone decreasing, so the final equality bound
is obtained directly from the actual coefficients, not a chosen tolerance.
At native wet coordinates, the maximum corresponding integral bound is
4.40624319e-8. Independently integrating this quadratic-source error equation at
the three native coordinates gives model-discrepancy values approximately
6.28682e-10, 5.05565e-9 and **1.05638e-8**, respectively. These are dimensionless
load bounds/estimates, not annual sediment kilograms, and do not include every
other floating-point or legacy approximation error. U11 separately sets the
exact dry-terminal load to zero.

## Disposition

The two sign changes are suitable to continue into broader validation. The
remaining observed negatives are quantitatively bounded terminal coefficient
precision, rather than the prior material negative-capacity region. That is
permission to test the candidate further, not permission to waive a gate.
Retain the three native-coordinate cases and the analytical bounds, keep all
existing water/particle/magnitude criteria unchanged, and extend the inventory
to the full matrix. Any negative support outside these proven terminal
conditions requires fresh disposition. Do not claim a strict raw-nonnegativity
pass or infer an annual-mass acceptance from the dimensionless bounds alone.

## Completed development-matrix terminal audit

The final independent audit verifies **1,188/1,188** exact-parity observations,
final result/receipt inventory equality, every input and output byte in both
observer and candidate directories, and source/binary hashes. The observer
binary is `d96ce37cda5bc78dfa66aab624ba7118d30c1a7d338c1d343f1c9945b4d98974`.
The candidate PARAM source remains the SHA stated above.

All **40,006** observed negative-capacity calls end exactly at the dry boundary
x=-qostar, have negative phi, and have theta=0. Their negative support is a
single strictly decreasing terminal band. Of these, 40,000 have a decreasing
polynomial throughout the retained interval. Six Charleston OFE2 calls have a
positive upstream hump; independent root reconstruction proves one negative
root outside the domain and one descending root immediately before the dry
endpoint. Their negative band itself satisfies the same bound, and all six
have zero representable negative wet coordinates. These newly observed shapes
were flagged before extending the proof; no unsupported class remains.

| Negative native wet coordinates per call | Calls |
| --- | ---: |
| 0 | 38,060 |
| 1 | 1,711 |
| 2 | 228 |
| 3 | 7 |

The 235 two/three-coordinate cases explicitly extend the original seed support
inventory. All native coordinates were enumerated; none were inferred from a
sampling grid. Final maxima, including ktrato, are:

- Negative-band width: **5.223192725e-8** nondimensional distance.
- Continuous terminal integral bound: **0.002760149342** dimensionless load.
- Integral bound at native wet coordinates: **0.001198802501**.
- Damped raw/clipped model discrepancy at native wet coordinates:
  **8.798294615e-7**.

The latter three maxima occur in Charleston 1718494 inbare/gravel/none,
year 15/day 324/OFE3, with ktrato=19297.837890625 and entry load=5256.48046875.
Large ktrato makes the dimensionless integral bound substantially larger than
the four-seed values; it must not be reported using the original seed maximum.
The damping-weighted value remains much smaller. The bound does not establish
annual sediment-mass error, does not include all floating-point/legacy limiter
effects, and does not prove the potential native coordinates were actually
queried by DEPOS. Exact dry-terminal load zero is a separate U11 convention.

Retained reproducible audit:

- `docs/work-packages/20261029_roads_parameterization_program/artifacts/audit_param_terminal_matrix_u12.py`
- `out/roads-parameterization-program-20261031/param-terminal-matrix-audit-u12/final-receipt.json`
- Final receipt SHA-256:
  `b768e3fbe05b21de714ddc601929efd33025a9ceb9d499db599eb21174dad6c5`.
- Audit script SHA-256:
  `5aa4beda66d077755b60fbd48faa1ea286c9da2ce2e8bbe8aa824f12b48f42e9`.

No additional blocking implementation finding was found in the U12 sign
change. This completes the requested full-matrix negative-support inventory;
the broader scientific, particle, water, watershed, and release gates retain
their separate acceptance authority. Do not claim strict raw nonnegativity.
