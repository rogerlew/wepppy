# Revision-4 buffer roughness persistence counterfactual

Status: predeclaration for independent scientific and implementation review.
No counterfactual binary has been built or executed. The active Roads program
ExecPlan remains authoritative; this is one diagnostic mechanism, not a release
candidate or accepted production parameter.

## Question and rationale

Does allowing the configured forest-buffer roughness to persist explain a
material part of the generated-soil sediment discrepancy, including effects on
water delivery and local sediment production? The accepted
[observation study](buffer-process-interpretation-r4/findings.md) found six
generated buffer histories decaying toward 6 mm while their legacy counterparts
retain 100 mm. Three generated underprediction controls retain 100 mm already.
The [frozen management metadata](buffer-roughness-counterfactual-r4-management-context.json)
represents forest conditions using Cropland Format.
This motivates a management/soil-conditioning compatibility test; it does not
establish that 100 mm is a physically correct forest roughness.

Frozen reference: revision-4 accepted engine SHA256
`2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48`,
with exact O3 observer SHA256
`ec9b733bb3336825a217d678dfa8f894c8d3cbf93437862c79a36223e7abc947`.
Reuse the same [nine pairs and dates](buffer-process-observation-r4/seeds.json),
whole legacy profiles and existing U12 `erosion_road_cap` generated candidate.
Do not introduce climates, materials, management values, soil translations,
withheld cases, new erosion coefficients or acceptance thresholds.

## One intervention and exact source placement

Lane `U1` retains the buffer's **post-native-initialization RRC** throughout the
original full 16-year period. Capture that REAL value once in SOIL's validated
initialization call, after native initialization and minimum handling. For this
panel the configured value is 0.1 m. Do not hard-code that number as a new
parameter or read mutable RRINIT as though it were permanently the initial value.

Restore only OFE 3 RRC after SOIL's complete native daily/initial roughness-writing
branch and **before CALL INFPAR**. SOIL owns all original direct RRC assignments.
The selected site precedes the first active downstream roughness consumer in
these no-tillage buffer decks and the subsequent SOIL critical-shear adjustment.
Preserve the native computations and overwrite only the declared RRC state.
Do not change bulk density, porosity, ridge height RH, rainfall accumulation,
management, conductivities, material classes, or any other input/state directly.

Fail closed outside the declared continuous three-OFE, cropland-format,
non-tilled buffer context. Capture the initial state before reading any daily
calendar variables. Require subsequent buffer RRINIT to equal its captured
initial value, and reject a management/tillage change rather than silently
changing the intervention. Initialization has its own literal phase/date marker;
it must not read an uninitialized year/day merely for diagnostics.

Natural consequences remain active:

| Consumer | Consequence that must remain native |
| --- | --- |
| INFPAR | Roughness-dependent crusting adjustment and effective conductivity |
| SOIL | Roughness-dependent critical-shear adjustment and its native cap |
| FRCFAC | Roughness/friction ratios and hydraulic friction |
| PARAM | Interrill roughness factor, class delivery weights, delivered source and theta |
| IRS | Depression storage and subsequent routing |
| TMPADJ, MELT and other active mapped readers | Existing full-history snow/thermal/diagnostic responses |
| SNDRFT | Reader exists, but its call is commented in this executable; no active pathway claim |

At 6 mm, the current PARAM formula reaches the upper roughness-factor bound;
at 100 mm it reaches zero, giving zero native interrill delivery weights in
this cropland-format branch. A sediment reduction can therefore include direct
interrill-source suppression. This is not a depression-storage-only experiment.
No derived correction may be frozen to its baseline value to conceal that effect.

## Lanes, controls and execution order

Build one private diagnostic binary from the exact frozen O3 source/object
closure, including its calendar sibling. An explicit run control selects:

- `O4`: observation/control off; no RRC assignment. Run all 18 lanes and require
  all seven ordinary outputs to match their original uninstrumented R4 bytes.
- `U1`: restore initial buffer RRC. Run all 18 lanes on exactly the same core and
  auxiliary inputs, full period and original target/prior-day observer selectors.

There are 36 new full-period runs. First preflight B1 legacy/modern in both modes
(four runs); only after all four gates pass execute the remaining 32. Retain all
attempts and bind exact scripts, map, patches, sources/includes/objects, compiler,
assembler/linker/libraries, binary, inputs, controls and dependencies before runs.
Use the system toolchain and pinned PATH; explicitly initialize the existing
PyArrow dataset reader before dependency discovery.

Expected null controls are the nine legacy lanes and the three generated
underprediction lanes B5/B6/B9. Prove them from native initial/pre-restore REAL
bits at every SOIL call, not from daily rounded SOIL output alone. If every
restore is an identity, require byte-identical ordinary outputs and matching
consumer observations after excluding only declared mode metadata. Unexpected
non-identity stops that control's interpretation; do not relabel it after seeing
outputs. Six generated lanes are expected to expose changed consumed RRC.

## Observability and invariants

Keep O3's original bounded event observations. Add guarded target/prior-day
observations at the actual producers for INFPAR crusting, SOIL roughness/shear
adjustment, FRCFAC friction, and PARAM rif/intdr/fidel/theta. An unexecuted branch
is explicitly unavailable; never print an unassigned local.

Add a separate full-period state-contract trace at every SOIL call for all three
OFEs: phase/date/OFE, mode, captured initial value, native pre-restore and consumed
post-restore RRC with REAL bit patterns, RRINIT, RH, and first-two-layer density
and porosity state, plus validated density drivers BDTLL/AO/BDCONS/COCA, day
counts and RFCUM. Record RH/RHINIT and residue SMRM as endogenous responses;
observe CBR only at its assigned decay branch. Record initialization separately and enforce exact expected
calendar ownership. No additional date selection or parameter search is allowed.

For every lane require native completion, correct UI/shared context, exact
ordinary/observer file inventories, unchanged input hashes, finite supported
states, canonical physical audits, and the unchanged versioned strict particle
audit. Rehash all source/input/output bytes afterward. A new unexplained flag
blocks acceptance; never renormalize fractions or loosen a threshold.

Require full-period road/fill WAT, ELEMENT and SOIL comparisons and state-contract
readback. The intended intervention is downstream of those OFEs, so unchanged
upstream outputs/states are the expected isolation result. Require exact paired BD/POR trajectories and their fixed density drivers under
these no-tillage, non-irrigated decks: BDTLL/AO/BDCONS/COCA, day counts and
climate-derived RFCUM. This follows the inspected producer paths, not a density
override. Unexpected differences require source-based classification and block
a clean isolation claim. RHINIT is 0.1 m in this panel, so native residue-mediated
RH changes are possible; observe RH/SMRM/CBR without making them exact-parity
requirements. Their direct equations and writes remain unchanged. Never force
state parity by overwriting an additional variable.

## Frozen assessments and stop rule

The primary assessment is the same three small-reference failing contrasts
B1/B2/B3; B8 supplies another overprediction contrast. Preserve B4/B7 passing
controls and B5/B6/B9 opposite-direction controls. Report all cases, including
worsening, null and unsupported responses.

Use the original annual magnitude envelope unchanged: for reference above
1 kg/year, candidate/reference must lie in [0.1, 10]; otherwise candidate must
be at most max(1, 10×reference) kg/year. Label target improvement only if at least
one originally failing selected case recovers this envelope, no originally
passing selected case regresses, and all physical/isolation gates pass. This is
a diagnostic result, not a parameter promotion gate or a complete matrix result.

Also report paired full-period and target-day surface water, hourly returns,
role-boundary sediment, signed net exchange, effective conductivity, critical
shear and interrill delivery. Distinguish bulk/net exchange from gross rates or
tagged provenance. Compare on minus off within each identical soil lane before
comparing legacy versus generated responses. Ratios with zero denominators stay
undefined; preserve signed differences. No outcome-dependent seed replacement.

Stop after this single scientific candidate. A null/worsening result is retained
and rejects the persistence hypothesis as a sufficient remedy for those outcomes;
it does not authorize fitting another roughness value. A runtime, provenance,
physical or isolation failure freezes interpretation until the concrete failure
is reviewed. Harness corrections may use new versioned attempts with the same
scientific rule; a different behavioral rule requires a new declaration.

Native ablation classification: `U1`, `boundary_disposition=requires_scientific_review`.
The O3 observations supply executed baseline evidence; numerical guards cannot
answer this process question. Native incident
`20261031_roads_buffer_roughness_counterfactual` retains the required scientific,
control and failure records. No release promotion, watchlist-resolution claim,
production deployment or UI implementation follows from this campaign.
