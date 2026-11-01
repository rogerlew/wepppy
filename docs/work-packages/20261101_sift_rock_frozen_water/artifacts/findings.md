# SIFT rock repair and frozen-water findings

## Production repair

BC SIFT's COFRAG volume percent now becomes WEPP RFG dry mass percent using the
source fine-earth bulk density and the native 2.65 g/cm3 mineral-fragment density
convention. At BD 1.3, source COFRAG 20 becomes 33.75796 mass percent, emitted as
33.8. Missing COFRAG or BD remains unavailable; invalid present values fail.
Original JSON and commented source columns retain the source values. Existing
soil files are unchanged until explicit rebuild. Open-water profiles retain their
canned path even when mineral inputs are invalid or absent.

The actual builder exposed two preexisting blockers that property-level tests
would miss: an undeclared prettytable import, and an OFE header missing SAT.
The bounded repairs use a standard-library comment table and explicit SAT 0.75.
This saturation is the established initialization convention, not measured BC
water content. Both changes were independently reviewed and recorded in
ADR-0126 before production editing. Baseline failing artifacts are retained.

Actual generated fixtures cover COFRAG 0, 20 and 80 percent at BD 1.3. They emit
0, 33.8 and 89.1 mass percent, retain the 200 mm horizon break and parse with the
canonical soil reader. Native mass interpretation is subject to the existing
85 percent cap, and the 2,000 mm emitted profile to the native 1,800 mm depth cap.
Native interpretation acceptance and final broad-suite disposition are recorded
in the validation artifact; neither implies empirical hydraulic calibration.

## Frozen-water mapping

The complete unchanged FRWATC routine, compiled with its exact 13 source/include
files and explicit COMMON initialization, ran 29 predeclared cases. All 18
normal controls conserve within the 2e-8 m fixture bound; the largest observed
normal residual is about 1.42e-9 m. Paired dry-reference shifts give identical
final fine-grid physical stocks and water fractions in the tested regime.

Five of the 11 threshold cases expose conservation discrepancies:

| Case | Observed discrepancy | Meaning |
| --- | --- | --- |
| F-low | Coarse stock omits about 0.270 mm | Two unfrozen fine supports below 1 mm are omitted during mapping. |
| G-low | About 0.020 mm incoming water remains unapplied, plus the 0.270 mm mapping omission | Final coarse-minus-requested is approximately -0.290 mm; these are separate mechanisms. |
| H-low | About 0.050 mm frozen-zone liquid is cleared | First mapping retains it in coarse stock; the next mapping loses it. |
| I-small | About 5.03e-8 m requested change is skipped | Absolute-delta threshold. |
| I-middle | About 4.99e-7 m requested change is skipped | Volumetric-change threshold. |

These are synthetic counterexamples, not measured annual losses. The nominal
1 mm fixtures compute slightly above the actual native REAL threshold and
therefore do not prove behavior at exact equality. No discrepancy is reassigned
to runoff, ET or another unobserved flux. Full stock calculations and signed
residuals are retained in frozen-summary.json and the independent scientific
review; raw source and executable evidence remain private.

## Decision and next work

Accept the independently validated dimensional writer repair separately from
native physics. Do not multiply all porosity or capacity consumers by a rock
factor: this campaign does not resolve downstream drainage domains, coupled
phase change or water/energy closure.

The next native study should trace these exact threshold paths in complete
histories, measuring invocation frequency, pre/post physical stocks and the
owner of every unapplied amount. Establish a reviewed support/residual-transfer
contract before testing any behavior change. Include multiple coarse layers,
shortage propagation and downstream drainage/percolation/tile/ET coupling. Keep
the earlier UL-minus-DRFC singularity counterexample as an independent gate.

Surface rock remains a separate evidence task. Survey surface-fragment records
are incomplete, and profile volume does not identify exposed rock area or its
overlap with vegetation. Preserve unknown versus measured zero and do not
promote a surface-cover or Roads armor default from this repair. The local BC
geodatabase was unavailable; synthetic conforming records and official metadata
do not constitute deployed-data validation. No production deployment, native
binary promotion, historical-run migration or withheld Roads evaluation occurs.
