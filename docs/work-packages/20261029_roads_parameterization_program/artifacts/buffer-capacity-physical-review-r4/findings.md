# Review separates water coordinates from a capacity-basis inconsistency

The retained evidence supports an internal coarse-fragment capacity-basis
inconsistency. It does not support changing the dry-water offset or refreshing
UL daily as a demonstrated remedy for the primary Roads sediment failures.
No native behavior was changed in this review.

## Physical interpretation

Let D be corrected dry-water depth, S the saved liquid above that reference,
U the native upper limit above that same reference, and P initialized air-corrected
pore depth. In the selected unfrozen observations, absolute liquid W = S + D,
absolute capacity C = U + D, and C equals P up to the recorded native rounding.
Thus U - S = C - W: the dry offset cancels at fixed absolute stock. The earlier
pore/dry/saved-liquid decomposition remains exact arithmetic, but its dry term
is not independently lost physical pore space. Dry-water parameters can affect
retention and history; this review does not declare them physically irrelevant.

Native SCON initialization sets absolute water using saturation times POR times
CPM times layer thickness. INFPAR also includes CPM in its effective saturation
ceiling. In contrast, the UL absolute ceiling is POR times thickness. POR already
contains air correction; CPM represents fine-earth volume under the native
mass-fraction/density convention. Applying CPM globally to POR would double
correct consumers that already use it.

[USDA's WEPP soil documentation](https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/chap7.pdf) defines effective porosity using both air and
coarse-fragment factors (chapter 7, equation 7.8.5). Its old mass-to-volume
conversion equation was corrected in a [2004 issue note](https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/docs/wepp_rock_correction_issue.pdf); the observed native CPM
matches the corrected conversion. The diagnostic here uses that native-interpreted
basis, not a claim that every emitted soil parameter is field-validated.

The selected generated-input audit establishes a mass-based RFG path: the
builder combines weight-based large-fragment and sieve fields, not the separate
volume metadata. All 108 upper-200-mm emitted horizon rows preserve their
retained source RFG. No input-unit repair is justified. Original raw sieve
measurements are absent, so field-data recomputation and representativeness
remain outside this result. See [input basis and lineage](rfg-basis.md).

## Retained observations

All nine pairs and both modes remain represented. The dry-coordinate identity
reconciles in all 556 consumed layer rows. There are 304 distinct owner-layer
snapshots after removing downstream reuse: 102 exceed the initialized POR*CPM
ceiling. Repeated consumption produces 196 excess rows; maximum per-layer excess
is 26.055 mm. These are selected windows from deliberately chosen histories,
including null-mode pairs, not independent samples or annual prevalence.

No observed state exceeds its native absolute ceiling. Contemporary POR without
adding the rock factor produces only 24 tiny apparent exceedances explained by
native rounding; none remains after explicit rounding separation. Contemporary
POR with CPM still gives 196 excess rows. This separates the rock-volume question
from daily porosity refresh; it does not establish complete water-budget closure.

INFPAR readback reproduces all 216 observed AVPOR and DTHETA values exactly in
native float32 order, including six reconstructed first clamps and 68 second
clamps. It uses the product of separately weighted mean POR and mean CPM, not
the mean of their layerwise product. These are parameter-calculation observations
at the SOIL/INFPAR clock, before later GRNA sampling. The reconstructed clamps
change AVSAT's infiltration proxy, not conserved ST: they are not water losses.

The primary generated B1/B2/B3 target events have no occupied-water excess under
the diagnostic. B2/B3's first-two-layer contributors have CPM=1, so this factor
cannot directly explain their target capacity deficit. Passing B4 and recovered
B8 generated histories do show substantial target excess. A consistency repair
cannot be marketed as a demonstrated primary-failure sediment remedy.

The [36 target rows](target-physical-basis.csv) retain both modes. With persistence
on, length-weighted positive local excess above the initialized air-and-rock
ceiling is shown below in mm. It is neither new runoff nor a signed whole-profile
water deficit; summing positive local excess preserves layer constraints.

| Case | Legacy diagnostic excess | Generated diagnostic excess |
| --- | ---: | ---: |
| B1 | 2.074 | 0 |
| B2 | 2.315 | 0 |
| B3 | 1.841 | 0 |
| B4 | 6.811 | 25.193 |
| B5 | 15.421 | 0 |
| B6 | 13.793 | 0.346 |
| B7 | 1.850 | 0 |
| B8 | 13.793 | 21.086 |
| B9 | 9.563 | 0 |

These are effective-capacity comparisons under the documented model convention,
not field-measured total pore-volume violations. Rock porosity and changing
entrapped air are not independently validated here.

## Decision and bounded next gates

Separate two questions. Reject an immediate daily UL refresh or dry-offset fit
from these observations. Advance a narrow capacity-basis contract/scalar study
before any behavioral full-model experiment: define whether limits, initial
water, retention, percolation and infiltration use bulk or fine-earth volume,
then test a consistent expression without changing POR globally.

Require zero-rock exact null controls, high-rock bounds and dry-floor/field-
capacity feasibility; test initialization, later capacity changes and ice
partitions separately. At unchanged absolute water, decreasing capacity cannot
silently delete excess or clip S. Any overflow must enter an explicitly owned,
measured flux or retained stock under a reviewed accounting contract. Do not
combine this with dynamic porosity, roughness, conductivity or depth changes.
A native behavioral lane requires its own frozen declaration, independent science
review, full-period parity/reference comparisons, physical accounting gates and
all passing/opposite controls. No rule, release or parameter is promoted here.

All original full-matrix gates, withheld materials and the human UI gate remain
unchanged. The Roads program remains active. [Reproduction](reproduce.md) covers
all seven numeric tables; [the next study specification](next-study.md) makes
the remaining contract/scalar work concrete without authorizing a production fix.
