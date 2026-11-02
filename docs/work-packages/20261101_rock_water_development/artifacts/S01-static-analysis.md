# S01: static SSURGO compensation analysis

S01 remains open. Read-only preparation/native analysis and an independent native
challenge establish noncommuting transformations and a source-level cross-OFE
coefficient ownership inconsistency. They do not measure heterogeneous runtime
impact or authorize a production repair. Existing bounded optional admission and
its recorded outputs remain valid within their actual support.

## Exact identity and evidence

The compiled source is `release-r5-renewed-pair-v2/candidate`, commit
`d2e14d96af5942409c9a315dc8594fcc164a702a`, bound by clean-build receipt
`8f97f78ab2119c1fcc91be62a0b0de36c2cf283c979a83a2ea9f430d7aafddbe`.
General binary SHA256 is `d81ade664de4b3af080b79192df29cb63b5d6ae210ea2a2fe1ba1c6593e19897`;
hill is `a031713759b3bed0412a9a2b7413d1fbabe9869f66d7611d7c4684042589a933`.
Sixteen relevant source units match committed blobs. `/workdir/wepp-forest` is a
modified checkout at `04f1c4d26bcef217009c124151f877dcbf3985cb`:397 of481
compared build-member names match,84 differ or are absent; both binaries differ.
It corroborates static scope but is not the admitted executable authority.

Private source anchors and complete identities remain under
`out/rock-water-development-20261101/supplementary-ssurgo-compensation-static-v1`:

| Packet | Bound manifest/receipt SHA256 |
| --- | --- |
| Native manifest | `a30d49e2b0f128e1f8f1c7cc78436af0afcda617c44b955a6d9ae1f1cdb1eedd` |
| Native receipt | `457b7563010a28e4eeb242474c08e524445905e1493a32765d33d58a3989be30` |
| Preparation manifest | `8785aab1b9f0bdbe5f156eee6cba728544871366a99b7b02c7483636ee6cb995` |
| Independent native receipt | `40dd536bff9f9659c951d183fa3ed537268595aa0c3fcb7111aa6f000b0a4bfb` |

No source listings are reproduced here. These packets performed no native runs,
builds, builders or production changes.

## Coordinates and operation order

Here w is rock **mass fraction**, rho is density in g/cm³, and theta is an
original source FC or WP volumetric fraction. Default preparation is
`theta/(1-min(w,0.5))`; optional preparation is `theta/c`, where
`c=2.65*(1-w)/(rho*w+2.65*(1-w))`. Native CPM uses the same functional form with
its effective density/rock operands (2650 when density is kg/m³). These are the
two existing policies and a native conversion, not three proposed formulas.

Final source FC/WP branches are selected independently; failed combined validation
can replace both with Rosetta. Optional eligibility requires both final branches
source-derived, original positive density, ordered physical source fractions and
the unchanged porosity/rock limits. Mixed/Rosetta or missing original density
remain excluded even if a later density estimate is plausible. Four-decimal
FC/WP and two-decimal BD/RFG serialization precede native conversion. Treatment
must preserve optional density/retention fields; MOFE concatenates complete
profiles, while staging clips depth without averaging their material.

Native INPUT clamps positive density to0.8–2.0g/cm³ and rock to85%, converts
units, adjusts profile support, and separately averages density, rock and retention
onto computational layers. Initialization TILAGE averages again before SCON.
SCON computes CPM, multiplies FC/WP, and applies its ordered moisture/porosity
corrections and floors. POR itself is not CPM-scaled. Initial relative storage
and UL use different CPM/reference expressions. Initial SOIL and later tillage/
reconsolidation can change density and POR without recomputing CPM or final FC/WP;
water-balance FC capacity/HK assignments are initialization-only. Source, emitted,
clamped, remapped, initial-tillage and later density therefore cannot be substituted
for one another. Relative ST alone is not absolute water: total soil water uses
ST plus FRZW plus the dry-reference depth contribution.

## Averaging does not generally invert compensation

For composed overlap weights a_ji, optional pre-guard retention is analytically
`C_j * sum_i(a_ji * theta_i/c_i)`, whereas weighted source retention is
`sum_i(a_ji * theta_i)`. Separately averaged/clamped density and rock determine
C_j. Equal source density alone does not make these expressions equal. Common c,
matching native c, compatible supports, rounding and inactive guards would also
need to be established. This algebra diagnoses noncommutativity; it is not a new
production policy or a complete floating-point replay.

Existing P03 records supply90 initialized layers; no model was rerun. Selected
OFE1 witnesses are volumetric fractions:

| Witness | Weighted source FC | Default final FC | Optional final FC | Optional minus source FC / WP |
| --- | ---: | ---: | ---: | ---: |
| H11 layer1, equal source density/mixed rock | 0.1945000041 | 0.2414333820 | 0.1951390207 | +0.0006390166 / +0.0003470489 |
| H28 layer3, mixed density/rock | 0.1653999984 | 0.2041079700 | 0.1670871824 | +0.0016871840 / −0.0000090086 |
| H28 layer4,0.78→0.80 density floor | 0.1390000000 | 0.1449533999 | 0.1373407394 | −0.0016592606 / −0.0006778558 |
| H40 layer1, density floor/mixed rock | 0.2675000039 | 0.2967370450 | 0.2672939897 | −0.0002060142 / −0.0000825956 |

No FC/WP guard fires in these witnesses. H11's ideal-composite FC residual is
+0.0006129517 before serialization/operation rounding; H28 layer4 is
−0.0016630817. Thus neither rounding alone nor the density floor alone explains
every discrepancy. These are input-dependent recovery residuals, not field errors
or sufficient evidence to change either policy.

## Cross-OFE owner must be observed before interpretation

Independent review confirms FC capacity and HK are layer-only shared arrays;
UL, retention and water states are layer-and-OFE indexed. Sequential initialization
writes FC/HK for each OFE; subsequent consumers lack a located reload. Each layer
slot retains its last initializing OFE, which need not be the final OFE for unequal
layer counts. PURK excess, PERC's sub0.95 saturation power, DRFC and drainage/lateral
paths consume these coefficients. Both continuous and general watershed source
paths exhibit the pattern. An unrelated local flag in WSHPAS is not a reload.

This establishes a source-level inconsistency for heterogeneous coefficients, but
no first actual misowned operand, changed hydrograph, affected-project count or
repair efficacy has been measured. All66 staged P03 hills repeat their profile
across OFEs; observed H11/H28/H40 initialization coefficients are identical across
their three OFEs. Positive domains and repeated-profile parity cannot discriminate
ownership. The next declaration must capture each initialized binary32 FC/HK and
its actual first consumer; HK requires positive excess and executed saturation
below0.95. Soil-order output differences alone are not an ownership oracle.

## Disposition and coordination

Retain the default and bounded optional policy while S01 remains open; defer any
default-change recommendation until the [gap matrix](S01-evidence-gap-matrix.md)
is resolved or explicitly bounded. The [retained comparison](S01-retained-comparison.md)
adds integrated native storage coordinates and a hash-bound prospective design.
Delegated experiment preparation/review stopped on agent usage limits; new native
execution remains pending. Broad-v1 has finished; broad-v2 is running. Preparation
is confirmed nonoverlapping by capacity_impl_review; heavy native execution needs
a coordinated parent gate. No new run, production/default change or deployment is
authorized by this report. Final reporting must retain S01's disposition and any
required soil/PASS/watershed rebuild compatibility.
