# D2 independent scientific review

Status: **accepted for scientific release as the exact revision-3 Linux pair**.
Fresh canonical outputs reproduce all 6,057 reviewed Cedar native files exactly,
and all final actual-binary gates pass. This is independent AI scientific review, not institutional peer review
or calibration against measured runoff/sediment. No canonical runtime source,
acceptance threshold, or other reviewer's artifact is modified by this reviewer.

## Invariants and source scope

The frozen candidate differs from revision 2 in exactly two native source units:
EPLANE and QINF. IRS passes the complete zero-based CDIST2 length array. Matching
that lower bound in EPLANE restores each OFE's own length/coefficient pairing;
index zero is outside the physical integration interval. This is an **interface correctness** repair, not a new hydraulic coefficient.
The correction retains the connected length and equilibrium-storage approximation. It does not reset
hydraulic support at OFE boundaries as rejected C3 did.

For uniform excess on a connected plane, the storage integral contains
`sum(integral(x_start, x_end) (x/alpha_i)^(1/m) dx)`. Equating that storage to
the equivalent uniform plane gives the existing EPLANE equation when the
correct local lengths are used. The actual native heterogeneous/sentinel and
non-first-root controls test this interface; homogeneous coefficients alone
can hide the former indexing error. The multiple-OFE construction and its
approximations are described in [WEPP Chapter 4](https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/chap4.pdf).

Let `T = ((fstar+1)/fstar)^(1/m)` for positive excess and recession infiltration.
The unchanged QINF equations are `Q*=1-m*tstar/((m+1)*T)` below T and
`Q*=(T/tstar)^m/(m+1)` above T. Both yield `1/(m+1)` at T and have derivative
`-m/((m+1)*T)` there. They are positive, at most one, and decrease with tstar.
There is no mathematical branch at unity. Its review classification is
**bounded_transition**, confined to this uniform-plane scalar domain. The former extra cutoff introduced
a finite jump, despite arbitrarily close event durations. The candidate removes
that cutoff without adding a runoff cap or changing equation coefficients.
The constant-excess/constant-recession-rate domain is explicit in
[Stone, Shirley and Lane (1993)](https://www.tucson.ars.ag.gov/unit/Publications/PDFfiles/944.pdf).

This scalar argument does not prove every heterogeneous or variable-forcing
application. The independent conservative finite-volume reference retains that
limitation. Readback confirms decreasing maximum runoff-fraction errors of
0.008137, 0.002072, and 0.000523 at 64, 256, and 1,024 cells, with maximum volume
residual 9.594e-13 and nonnegative surface storage. No post-result tolerance
change was needed. This is not a proof of the separate soil-state/capacity-order
contract (SC-WATBAL-001#INV-WATBAL-002); historical unobserved or review-required
findings for that contract remain unchanged.

## Explicit local source audit

The rejected U1-only counterexample remains relevant. At delayed-return year 1,
day 9, OFE 2, the combined candidate has local supply 0.698124621 m³ and
accepted upstream Hortonian supply 1.410935473 m³. Outgoing Hortonian volume is
1.725927984 m³, leaving positive FIN of 0.383132129 m³ within rounding. There is
no surface-source excess and no need to relabel soil stock or lateral soil flow
as a surface supply. In this same frame, correcting the length association
changes equivalent alpha from U1's 1.51931417 to 0.50755137: the upstream
hydraulic resistance is restored. The origin-only U2 control independently
produces positive FIN of 0.383124443 m³. Thus the factorial evidence supports
the geometry correction's causal role, while scalar continuity has its own
separate domain justification.

Independent readback covers all 210,384 U3 accounting states. Zero linked QINF
states have negative total FIN at the existing displayed-volume criterion.
However, **93 total FIN states remain negative elsewhere**: all are ROCHEK
states with explicit positive upstream surface return. Return plus FIN is at
least 0.189284 m³ in those cases. Therefore the release must not claim all
negative FIN was eliminated or globally prohibit legitimate signed exchanges.
Maximum reconstructed surface-identity rounding residual is 1.3921e-6 m³.

There are still 413 negative differences between successive cumulative
recession estimates. They are not independently accepted as physical negative
infiltration; the net local surface exchange and its actual sources are the
relevant checks. The bounded evidence does not establish universal component
ownership in heterogeneous chains. Both U2 and U3 remain retained factorial
lanes, and U1's failed source gate is not erased.

Executable readback and hashes are in `D2-scientific-source-audit.py` and
`D2-scientific-source-audit.json`.

## Fresh candidate Cedar semantics

The clean D2 candidate completes all 864 hillslopes and all 24 watershed years.
Native conversion accepts 7,573,824 PASS and 16,690,464 WAT records with zero
rejections. Audited water fields and particle concentrations/fractions have no
negative or nonfinite values; particle fields also have no nulls.

Against revision 2, printed outlet sediment changes from 517,815.77 to
517,670.63 kg, a reduction of 145.14 kg (0.028029%). Annual sediment changes
range from -0.244772% to +0.009982%. The largest daily absolute sediment change
is -13.91 kg on 1988-11-21. A smaller event on 1997-07-09 decreases from
24.56 to 13.08 kg (-46.74%); modest aggregate changes do not imply all individual
events are relatively unchanged.

Published water volume decreases by 26.61 m³ (0.000002099%). Maximum sampled
peak remains 46.2 m³/s at the same time. Maximum reported peak decreases by
0.00727 m³/s; the largest daily reported-peak change is +0.0369 m³/s. The
sampled peak's largest daily difference is 0.1 m³/s, which must be distinguished
from the more finely printed reported peak. Selected event peak changes range
from -3.0875% to +0.5917%, and discharge-centroid shifts from -2.271 to +2.087
minutes. Neither conserved volume nor an unchanged maximum establishes timing
validation by itself; these event checks provide the additional evidence.

The sampled hydrograph volume sum changes by -4,711.38 m³, unlike the native
published volume sum. Sampling and printed-discharge quadrature are not an
independent physical water budget. Both lanes have zero days outside the
retained conservative publication-rounding check. Do not characterize the
difference between these publication products as unaccounted model water.

WAT changes on 29 of 481 single-OFE hillslopes and 26 of 383 multi-OFE hillslopes.
The single-OFE effects arise from QINF's domain extension; EPLANE is not called
for those single-OFE cases. This repair therefore has scientifically relevant
scope outside Roads. `D2-scientific-semantic-audit.json` retains file comparisons,
daily extremes, annual/monthly groups, particle and water checks.

The observation panel was frozen before replay: the established sixteen dates
plus the three largest absolute changes in native published volume, reported
peak, and sediment, each with the preceding day (34 distinct dates). The
full-period class-sign check is independent of that date selection. New dates
have candidate local source/bed checks; the retained sixteen also have matched
revision-2 channel detail. `D2-scientific-event-selection.json` records the rule
and exact native EBE hashes.

## Release requirements and limits

The 840-case development panel remains physically valid, but the magnitude
objective remains unmet: 713/766 meaningful references and 31/74 small references,
compared with revision 2's 719/766 and 30/74. Two cases recover and seven regress.
That does not refute a demonstrated interface/domain repair, but it prohibits
presenting the change as a general sediment-calibration improvement or using it
to justify a uniform erosion reduction. Roads defaults and the human UI gate
remain separate.

The fresh candidate Cedar semantic/particle and channel observation checks
pass. The observation replay uses the candidate's own fresh PASS files and
reproduces all nine standard watershed outputs exactly. There are zero negative
or nonfinite intermediate class transfers over the full 24 years.

All 34 declared dates pass candidate local accounting: 12,614 channel-events
and 63,070 source-class records. Maximum relative lateral-source residual is
2.0353e-7 after the retained 0.99998898248 unit roundtrip; maximum relative local
signed-bed closure residual is 2.7799e-8. Segment joins are exact; maximum
publication-versus-segment difference is 0.00247 kg. On the sixteen dates with
paired revision-2 detail, the maximum absolute change in event-summed local
erosion is 0.627 kg and deposition is 2.261 kg. These local/panel identities
are not a closed whole-watershed sediment budget. The executable evidence is
`D2-scientific-channel-audit.py` and `D2-scientific-channel-audit.json`.

The exact dated pair from source `6112b68bce0e21a77f510bde5c24af067a47a647`
is accepted for scientific release. Its fresh 864-hillslope/24-year Cedar run
reproduces all 6,057 reviewed native outputs exactly. The independent observer
therefore transfers by demonstrated output equality, not assumed compiler or
source equivalence. All 1,095 native tests, 28 watchlist cases, 99 Disturbed tests,
840 Roads physical cases, 12 clean full-period comparisons, and two host smokes
pass on the final dated binaries. Roads inputs and outputs are exact against D2.
Disturbed outputs are exact; each of 96 generated soil decks differs only in
one same-position Build Date comment, with every other byte equal. These inputs
are not claimed byte-identical.

`D2-final-scientific-acceptance.json` binds both binary SHA-256 identities, source,
scientific classifications, caveats, and evidence hashes. Its executable
`D2-scientific-final-binding.py` verifies the final receipts and provenance.
This scientific acceptance does not waive separate application, publication,
provenance, or deployment gates, and does not accept Roads calibration defaults.
