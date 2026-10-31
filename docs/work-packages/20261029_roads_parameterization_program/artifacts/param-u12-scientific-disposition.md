# Combined U12 scientific disposition

Status: **scientifically accepted for native repair promotion; all declared
scientific gates are complete**. This review concerns the exact
combined native repair candidate, not acceptance of Roads parameterization or its
configuration UI.

Candidate executable hashes:

- `wepp`: `2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48`
- `wepp_hill`: `9ef6b62677407a66255a2b95becc9f350c87ef8e4cf67ab4e543ddb89ed4a010`

The source/build manifests and run evidence are under
`out/roads-parameterization-program-20261031/param-sign-u12-combined/`.

## Scientific findings and acceptance limits

1. **No unexplained fraction-accounting mismatch remains in the two flagged
   Roads/downstream events.** Both have exact source-state replay and
   operation-derived finite-precision bounds, with applicability checked against
   the exact U12 binary. The unchanged strict audit still reports both fraction
   flags. Calling these observed residuals explained satisfies the plan's
   *unexplained accounting mismatch* requirement for these events without making
   the printing-only predicate pass or altering any tolerance. The detailed
   [fraction disposition](fraction-arithmetic-scientific-disposition.md) defines
   the proof, mass scale, source hashes, and reuse limits.
2. **The residual raw-versus-clipped capacity discrepancy has a demonstrated
   terminal-boundary mechanism across the complete observed matrix.** The
   completed inventory includes narrow negative bands with zero through three
   representable wet coordinates, and six positive upstream humps whose negative
   support is confined to the descending terminal band. The supporting proof
   applies on that local band; whole-interval monotonicity is unnecessary. It is
   incorrect to claim raw capacity is everywhere nonnegative or that all negative
   support lies outside native coordinates. All 1,188 observations have exact
   ordinary-output parity, complete inventory equality, and rehashed observer
   and candidate input/output bytes. The residual is quantitatively explained;
   it is not a strict raw-capacity-nonnegativity pass.
3. **Cedar's completed watershed semantic, particle, and source review passes.**
   Independent byte verification confirms identical source inputs and raw water/
   soil outputs against U11 and revision 3. Sediment outputs have real changes;
   they are not described as metadata-only differences. Detailed scope and
   physical-water-budget limitations are below.
4. **Roads parameterization remains scientifically unaccepted.** The native
   repair does not change any magnitude classification: 713/766 meaningful-load
   cases and 31/74 small-load cases pass their frozen criteria. This is 744/840
   overall; it does not satisfy the program's 95% overall requirement. No UI
   implementation or parameter-default promotion follows from native numerical
   acceptance.

## Completed generated-output evidence

The retained [gate receipt](param-u12-gates-in-progress.json) records 1,253 native
tests, 28 watchlist cases, 99 Disturbed cases, and both executable smoke checks
passing. This reviewer verified the hashes of all ten retained gate logs and
their completion summaries. These shared-code regression checks are supplemented
by the completed Cedar semantic review below.

The [paired output review](param-u12-scientific-output-review.json), produced by
[its retained checker](review_param_sign_u12_outputs.py), verifies generated input
hashes, source-record provenance, ordinary output hashes, prior physical checks,
and the unchanged magnitude formulas. The comparison is against the declared
original Roads/downstream sources, not an attribution of every change solely to
the final PARAM edit.

| Panel | Completed prior physical audit | Annual export changes | Frozen magnitude outcomes |
| --- | --- | --- | --- |
| Roads | 840/840 | 152 increases, 12 decreases, 676 unchanged | 713/766 meaningful; 31/74 small |
| Downstream | 348/348 | 11 increases, 16 decreases, 320 unchanged; one recovered native stop | 143/213 meaningful; 9/135 small |

No previously passing magnitude classification regresses, and no previously
failing classification recovers. Water and soil outputs are byte-identical for
all 1,187 previously successful paired cases. The recovered downstream native
failure has a complete new simulation; its previously interrupted files are not
a valid full-period parity control. Its sediment result remains outside the
magnitude target.

The largest absolute Roads annual-export change is a reduction from
214.1036743 to 198.4133708 kg/year for site/1718465/outunrut/gravel/none. The
largest downstream change is buffer_cap for the same configuration, from
446.0529136 to 429.2849794 kg/year. Both remain in their prior magnitude class.
The presence of both increases and decreases is consistent with repairing source
support, load continuity, and deposition numerics; this repair is not a universal
sediment reduction factor or calibration.

Expanded particle audits cover every EVENT: 117,145 Roads records with 96,775
positive-sediment records, plus 18,620 downstream records with 13,105 positive
records. They retain exactly two fraction-only flags and no class/bulk mass
flags. The audit script hash remains
`f8c3c21b00d90f507106c6b5c813d646fbf7e7a6fcb978223efb9c4189412302`.
Tiny SUBEVENT/no-event exports are outside this particular EVENT audit; other
output and source gates remain necessary.

## Completed Cedar review

The [independent Cedar receipt](param-u12-cedar-scientific-review.json) and its
[retained checker](review_param_u12_cedar.py) verify actual bytes, not just equal
manifest strings. All 5,201 recorded inputs, all 864 raw WAT files, and all 864
raw soil output files match across U12, U11, and the revision-3 reference.
Semantic-analysis inputs and outputs, converted files, audit sources, and the
exact native executable pair were rehashed. Separately, all 480 source-file
hashes in the U12 source manifest match both the frozen build inputs and the
current native checkout; see the
[source verification](param-u12-source-scientific-verification.json).
The nine additional FPM/include-tree files also match the native checkout and
frozen build; see the independently rechecked
[additional source verification](param-u12-additional-source-verification.json).

The watershed completes all 24 years, 1980–2003, with return code zero. Fresh
conversion accepts all 7,573,824 PASS and 16,690,464 WAT records with zero rejects
over 8,766 dates. The 17 audited water fields are finite and nonnegative, and
the ten particle concentration/fraction fields have no negative, nonfinite, or
null values.

All reported U12 semantic candidate metrics exactly match U11. Relative to
revision 3, sampled and published discharge volumes, hillslope surface/lateral/
baseflow contributions, annual discharge peaks, and all 358 descriptive event
windows remain unchanged. Total published sediment is 517,671.83 kg versus
517,670.63 kg, an increase of 1.2 kg over 24 years (0.0002318%). This is a small
shared-routing result, not a calibration improvement or a claim that every
sediment distribution is unchanged.

Relative to U11, four raw output files change: `H296.ebe.dat`,
`H296.element.dat`, `H296.pass.dat`, and `pass_pw0.txt`. These include real
deposition/particle-class changes at tiny export loads. Converted Parquet hash
differences were not assumed to be metadata-only. Raw water/soil parity is
established independently, and unchanged semantic totals do not imply parity of
all sediment records.

The discharge checks demonstrate publication consistency, not a universal
physical water budget. Printed sampling and reconstructed initial discharge
retain their documented rounding/first-day limitations. The Cedar particle
audit demonstrates finite, nonnegative concentrations and fractions; it is not
an all-event class-versus-bulk mass-closure proof. The narrower Roads/downstream
Decimal audit and its two source-specific numerical certificates remain separate.

## Mechanism, precision, and shared scope

The accepted candidate retains the separately tested DEPEND root safeguards,
EROD interval/transition support and stiff-step treatment, common capacity
evaluation, actual-load handoffs, and the strict wet-domain coordinate contract.
The U12 addition changes only which side of the existing denominator floor is
used when a shear or transport continuity denominator rounds exactly to zero
with a nonnegative first slope.

For the positive physical continuity product `t`, `r=1/(t-1)` implies
`1+r=t/(t-1)`: as `t` approaches zero from above, the denominator approaches zero
from below. The former positive zero guard reversed the polynomial's sign when
REAL rounding produced `r=-1`. Selecting the negative side restores the observed
producer limit. Both guards retain their existing 0.001 floor, all nonzero
denominator branches, and the negative-first-slope behavior. This restores the
side of the limit, not its exact magnitude. Zero slope adopts the nonnegative
one-sided continuation. Normal producer, fallback, slope-sign, and threshold
controls remain part of the retained review evidence.

The remaining negative terminal bands arise from finite-precision polynomial
coefficients near the exact dry endpoint. For raw capacity `Craw`, clipped
capacity `Cclip`, and equal load at entry to a negative band, the continuous
load discrepancy obeys:

```text
E' + [phi/(x+qostar)] E = Cclip' - Craw'.
```

On the observed wet negative-flow support, the coefficient is positive, so the
integrating-factor kernel is at most one. Thus `|E|` is bounded by the integral
of `|Craw'|` over the negative band. The exact weighted quadratic-source solution
provides a sharper bound at representable wet coordinates. These are
source-derived dimensionless load discrepancies, not fitted tolerances or annual
mass allowances. They do not include every other rounding or model-approximation
error. Exact dry-terminal output uses the separately tested zero-load convention.
The final 1,188-case inventory contains 40,006 negative-capacity observations,
all with zero interrill source. Of these, 40,000 have whole-interval monotone
capacity and six have a positive upstream hump followed by the same monotone
negative tail. Native negative wet-coordinate counts are: 38,060 with zero,
1,711 with one, 228 with two, and seven with three. There are no unclassified
support regions. Maximum negative-band width is 5.2231927253e-8 normalized
distance. Maximum continuous terminal integral bound is 0.0027601493425,
maximum native-wet integral bound is 0.0011988025011, and maximum exact weighted
native-coordinate discrepancy is 8.7982946151e-7, all in dimensionless load
where applicable. These different quantities must not be conflated.

The complete receipt is
`out/roads-parameterization-program-20261031/param-terminal-matrix-audit-u12/final-receipt.json`,
SHA-256 `b768e3fbe05b21de714ddc601929efd33025a9ceb9d499db599eb21174dad6c5`.
This reviewer verified that hash, final inventory flags, all local support
preconditions, and the absence of unresolved support classes. The retained
[terminal audit](audit_param_terminal_matrix_u12.py) includes exact-input roots,
the local-band proof conditions, and the weighted solution with removable
`-phi=1` and `-phi=2` limits.
Supplementary independent 80-digit quadrature verifies 22 native-coordinate
checks from the 12 distinct largest-discrepancy states, plus synthetic limiting
and concave-hump cases; maximum relative difference is 1.42895e-74. Its receipt
under the same directory is `quadrature-verification.json`, SHA-256
`786ae6fbedf3570427e2436fe5cd9cee29f3cf3c316ef4486dfb6d4d7a2af608`.
This formula cross-check supplements, rather than replaces, the complete
40,006-call support inventory.

These routines are shared native sediment routing, not Roads-only parameter
tables. Disturbed and Cedar therefore remain required regression panels. Model
agreement here does not establish field calibration, universal watershed
closure, or physical validity for unsupported polynomial domains. Any future
negative support outside the proven terminal-band conditions needs a fresh
review rather than reuse of this certificate.

## Promotion decision

The completed evidence supports promotion of the exact combined U12 native
repair pair stated above. No unresolved scientific blocker remains within the
declared validation panels. The two specific *unexplained fraction accounting*
findings and observed terminal-capacity discrepancies are closed by retained
source-derived numerical explanations; their strict audit predicates remain
unchanged and visible. This is not a declaration of exact arithmetic closure,
universal model validity, or absence of changes in sediment distributions.

The [final scientific acceptance receipt](param-u12-scientific-acceptance.json)
binds this decision to the executable pair and evidence hashes. A different
binary requires renewed applicability review. Native repair acceptance remains
separate from the still-failing Roads magnitude program and its human-gated UI
specification/layout. This review performs no production deployment.
