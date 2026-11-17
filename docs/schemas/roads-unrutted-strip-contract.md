# Unrutted partial-crossing strip contract

Status: accepted 2026-11-17 by Roger Lew; both independent contract reviews pass.
Implementation conformance pending. RUPC-01 supersedes conflicting unrutted geometry
and eligibility provisions in the Roads specification after this standalone
checkpoint. Current deployed behavior is unchanged.

## Scope and rationale

RUPC-01 models contour-following unrutted roads as simplified parallel hillslope
profiles. It replaces longitudinal segmentation and whole-hillslope 60% eligibility
for this design. Insloped and rutted models remain unchanged. A strip is an area
allocation, not a verified terrain flowpath partition. Switchbacks, shared upslope
contributing areas, and sequential multiple-crossing connectivity are not resolved.
This limitation must appear in user help and retained execution provenance.

## Preparation and crossing identity

For `outslope_unrutted` (including existing aliases), preserve line geometry through
longitudinal elevation reversals. Continue valid DEM intersection/sampling and
existing source attribute mapping; do not manufacture geometry outside valid data.
Keep point-source low-point/monotonic preparation unchanged for other designs.

Dissolve hillslope polygon parts by TOPAZ ID before intersection. Crossing identity
is local to preparation, never a stable cross-preparation ID. Within one hillslope,
connected road pieces with identical effective model inputs must be coalesced
before the minimum-length and crossing-cap checks;
conflicting attributes must not be discarded. Exact duplicate geometry with identical
inputs is counted once. Distinct overlapping records with conflicting model inputs
must produce an explicit ambiguity error rather than silent first-record selection.
Define effective inputs using existing field mapping/default resolution, including
width, surface, traffic, soil and required fill/buffer values; source labels and
uploaded length labels are not model inputs. Treat each connected component of the exact geometric union as one crossing,
including a branched component; do not snap near endpoints or infer drainage
connectivity. Do not join disjoint pieces merely because their attributes match.
Retain source membership as diagnostic provenance. Canonicalize component geometry
for tie-breaking so reversing line direction or reordering features does not change
cap selection. Conflicting overlaps mean positive shared centerline length, not a
single crossing point.

Retain physical overlap minimum 10 m and the deterministic maximum of three
crossings per hillslope (descending overlap, deterministic geometric tie-break).
Remove the 0.60 eligibility cutoff; retain inclusion-ratio diagnostics as descriptive
values. Existing excluded-by-cap/minimum contributions remain explicitly reported.
Area preservation objectives below refer to included crossings; also report target
road area excluded by eligibility/cap so inclusion loss cannot be concealed.

## Strip geometry

Let original modeled hillslope width be W and length H; its reference area is W*H.
For included crossing i, let L_i be geodesic in-hillslope centerline length, and
b_i be resolved physical road width. All dimensions must be finite and positive.
Road target area A_i = L_i*b_i. Do not use an uploaded length attribute in place
of measured overlap. Physical width retains its existing valid range.

Set width factor f = min(1, W/sum(L_i)), and strip width w_i = f*L_i. Set road OFE
length r_i = b_i and slope 0.04 (4%). This explicitly replaces the legacy unrutted
longitudinal-slope parity transform; it does not change soil or management selection.
The modeled road area is w_i*r_i, with deficit A_i - w_i*r_i. When f < 1, record
reason `hillslope_width_limit` and the deficit; do not secretly lengthen the road
OFE, invent terrain connectivity, or increase hillslope area to absorb road length.
When f = 1, road area must match its target to rounding precision.

Use the existing distance-to-channel median placement and supplied fill dimensions.
Downstream landuse length is max(0, D_med - fill_length); collapse it to zero when
below the existing 10 m threshold. Upslope length is H minus road, fill and downstream
lengths. All present OFEs must have positive lengths; fail the affected replacement
explicitly if there is no positive upslope length. Preserve existing required
fill/buffer validation; no new missing-input defaults. Existing missing-distance
fallback must be identified in provenance if used, not described as measured position.

Unaffected remainder width is W-sum(w_i), with original H. Initially every affected strip has total length H. Preserve the existing small
remainder rule: if remainder width is positive but below 0.3 m, transfer its area
to the first deterministically ordered strip by extending only upstream landuse
length by remainder_area / strip_width; set remainder width to zero. This explicit
exception preserves total area without creating a tiny native remainder profile.
Thus sum(strip areas)+remainder area = W*H by construction.
Retain existing residual compensation on upstream landuse for floating-point error
only; numerical acceptance is absolute area error <= 1e-6 square meters in planned
geometry. No relative tolerance. Reject non-finite values and non-positive
compensated lengths. For unrutted slope files, serialize dimensions with 12 decimal places and parse
back the emitted dimensions before execution; enforce the same 1e-6 square meter
absolute bound on the sum of consumed profile areas. Reject zero/negative emitted
length or width. Other road writers retain their formatting. Native WAT/PASS header
rounding remains governed by the existing modeled-area accounting contract: retain
full source areas and report serialized reconciliation rather than silently
rescaling responses to force equality. The exact area invariant is for planned
and emitted geometry; native output serialization differences must be visible.

## PASS replacement and results

Run each strip and positive-area remainder separately. Use the existing phase4
replacement combiner, preserving its event and unit semantics. Never include the
original baseline hillslope PASS alongside its replacement contributors. Retain
original watershed hillslope IDs and topology. No new queue or combiner algorithm.
No-road partitioned controls use the actual original baseline slope, soil,
management, climate, OFE ordering and native binary; vary only profile widths,
partitioning original width between two equal-width profiles. Do not substitute
road-buffer templates as baseline landuse. Compare annual and whole-period runoff
volume and sediment mass, and event count/calendar, against the unpartitioned
baseline, recording absolute/relative differences (relative difference null for a
zero baseline). This is a diagnostic of partition effects, not a scientific
response-equivalence release threshold; numerical area closure, finite complete
outputs and correct PASS aggregation remain release gates. Do not claim identical
response solely from conserved area. Retain existing unaffected-remainder
parameterization separately and label it honestly; changing that scientific
parameterization is outside this amendment.

Preserve public keys; append `geometry_policy: unrutted_strips_v1`, reference area,
affected area, remainder area, area residual, road target/modeled/deficit areas,
width factor, eligibility losses and connectivity limitation to retained accounting
and summary records. Use keys `reference_area_m2`, `affected_area_m2`, `remainder_area_m2`,
`area_residual_m2`, `road_target_area_m2`, `road_modeled_area_m2`,
`road_area_deficit_m2`, `strip_width_factor`, `excluded_road_target_area_m2`,
and `connectivity_limitation`. Reference/excluded/remainder totals are hillslope
fields; crossing records carry road target/modeled/deficit and width factor.
Hillslope records live in `outslope_unrutted_hillslope_records` in the run summary;
crossing fields live in `segment_execution_records` and the segment PASS manifest.
Copy these values from one computed plan rather than recomputing per consumer.
`geometry_policy` and `connectivity_limitation` are strings; all `_m2` fields are
finite numbers in square meters, and width factor is dimensionless in (0,1].
Road target/modeled/deficit totals cover included crossings;
`excluded_road_target_area_m2` covers minimum/cap exclusions separately.
For failed or unresolvable records, unavailable numeric fields are JSON null, never
zero; provide `area_accounting_status` (`complete`, `partial`, or `unavailable`)
and `area_accounting_reason` (null on complete records). Missing widths in excluded
records produce partial excluded totals with `excluded_road_area_unknown_count`;
do not imply the known subtotal covers unknown source area. Preserve existing
status/reason keys. No NaN/Infinity in serialized JSON. Keep per-crossing values as well
as hillslope totals. Inputs, planned geometry, native inputs, failures, PASS files
and provenance remain inspectable through existing browse/archive mechanisms.

## Lifecycle and errors

New preparation records `unrutted_geometry_policy: unrutted_strips_v1` in the
existing prepare summary. Running an unrutted project from an older prepared set
requires Prepare again; no silent conversion of old candidates. This is a policy
marker, not a new identity service. No changes to historical result files on read.
Use existing current-result eligibility/retention rules; newly failed or stale
attempts cannot publish old results as fresh. Archive/restore retains the marker
and all ordinary retained evidence. Non-unrutted preparation remains compatible.

Missing required dimensions, non-finite geometry, ambiguous conflicting overlaps,
non-positive profile lengths produce explicit bounded domain failures before
result comparison/publication. A valid zero-contributor run remains a successful
baseline-equivalent outcome under the modeled-area accounting contract, with zero
executed-road metrics and an explicit no-road-effect diagnostic; comparison
generation must support this state. Distinguish that valid absence from attempted
contributor execution failures, which remain failures. Include actionable
recovery guidance and retain failure evidence. No late empty-comparison exception may replace the valid no-contributor outcome.

## Validation and authority

Tests are scoped to changed paths and affected consumers by explicit operator
instruction. Native input/PASS/watershed readback and 141/42 cases on a disposable
forest project are required. Geometry invariants, invalidation, and other road
regimes need focused regressions. Formula approval, two independent contract
reviews and a standalone checkpoint ancestor are required before code edits.

See [ADR-0146](../adrs/ADR-0146-unrutted-partial-crossing-strips.md) and
[work package](../work-packages/20261117_roads_unrutted_partial_crossings/package.md).
