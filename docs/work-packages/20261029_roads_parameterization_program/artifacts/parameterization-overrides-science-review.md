# Independent road override characterization review

Reviewer: `override_protocol_review`, 2026-11-03. **PASS for the bounded 18-profile
road-role characterization**, not field calibration or production workflow closure.

The operative v5 declaration is SHA256
`5027d7fcb802f18d5e20743d3c6e4e8c77aaa34db1347e23503c34daa32aaaab`;
results SHA256 is
`e51100d2460c7f47051390c59af71a7ed8b064dff1b643fe4c0593acf66d7bd0`.
The [protocol review](parameterization-overrides-protocol-review.md) retains
preexecution findings, revoked v2 approval and unused v3/v4 amendments. No native
calls preceded v5 approval. Both baseline contexts and all sixteen contrasts
completed once, with no native reruns.

## Independent artifact readback

[Executable readback](parameterization_overrides_independent_readback.py) verified
all 141 declared dependency hashes, each prepared input and all seven raw output
hashes per case (126 outputs). It independently accumulated raw PASS volume and
volume-times-concentration using Decimal arithmetic and matched production annual
runoff/sediment summaries for all 18 profiles. It verified every daily PASS date
(16 years, 2000–2015), parsed raw fixed-width ELEMENT records and independently
recomputed each OFE boundary export. Unchanged strict particle predicates passed
all 18 cases using their actual terminal OFE, with zero flags.

The machine-readable [readback](parameterization-overrides-independent-readback.json)
binds exact results, reader source and output hashes. Raw evidence is under
`/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-overrides-v1`.
The first independent reader attempt omitted EVENT SRC3 trailer handling and
failed before producing a receipt. Its script and failure receipt are retained
as `independent-readback-v1.py` and `independent-readback-v1-failure.json` in that
root; the corrected reader passed without altering model inputs or outputs.

## Supported conclusions

For the declared gravel/loam/low-traffic road-only context, half/double road AVKE
changed annual PASS runoff by +95.11% / -39.79% and sediment by +49.82% / -37.55%.
Half/double Ki changed sediment by -43.76% / +87.51%; Kr by -6.23% / +12.46%;
critical shear by +15.01% / -3.36%. Erosion-coefficient contrasts left runoff
unchanged. Each contrast changes exactly one road-header scalar, after traffic
resolution, with unchanged geometry, management, climate, sidecars and other roles.

The road/fill/buffer context demonstrates downstream attenuation and coupling:
half/double road AVKE changed outlet runoff by +2.25% / -1.02% and sediment by
+32.34% / -18.90%. Road Ki, Kr and critical shear retained the expected sediment
response directions, with unchanged runoff. This supports offering explicit road
coefficient controls and showing both source and final role values. It does not
support a universal response magnitude or a promised proportional sediment slider.

PASS sediment is EVENT-supported export. Full terminal ELEMENT sediment differs
because non-EVENT sediment has no PASS particle payload; both are retained and
must not be conflated. The physical gate covers finite/nonnegative water/sediment,
complete role calendars, actual areas and existing printed-report reconciliation.
It does not certify full internal water-storage or cross-role transfer closure.

## Scope limits

Only road coefficients were varied, in one texture/surface/traffic/climate and two
role arrangements. Fill/buffer override sensitivity, paved behavior, other textures,
other climates and route combinations are not characterized by these 18 calls.
Source evidence can establish their supported inputs, but their response evidence
must remain labeled separately. Half/double are study values, not recommended or
validated API bounds. No real project, default, shared soil, withheld material,
production wiring, installed native binary or numerical audit tolerance changed.

## Supplemental event-adjusted coefficient review

Independently parsed raw fixed-width ELEMENT rows for all 18 profiles and all
36 OFE role instances. Recomputed minimum/maximum Keff, Ki, Kr and Tcrit and matched
all ranges in `runtime-coefficient-readback.json`. Verified installed source
`sedout.for` byte-for-byte against r7 commit: it prints Keff in mm/h, adjusted Ki
scaled by 1e-6, adjusted Kr scaled by 1000, and adjusted critical shear in Pa.
The supplemental reader correctly restores Ki/Kr physical units and preserves
the distinction between input baseline and event-adjusted coefficients. A road
baseline input shear of 2 Pa therefore need not equal its first-event Tcrit of 4 Pa.

Raw `runtime-coefficient-independent-readback.json` retains the 36 role checks,
source commit/hash and reviewed runtime receipt hash. The final human-readable
results accurately state response direction, coupling and scope limits. Their
scientific conclusions pass; actual wired UI/persistence remains outside this
characterization review.
