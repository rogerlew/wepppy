# Independent scientific review: WEPP 261029

Date: 2026-10-30. Reviewer: Codex agent `/root/scientific_review`, separately
assigned after implementation. This is independent AI review of the submitted
work, not human peer review, institutional endorsement, or field validation.

## Recommendation

Accept the matched Linux 261029 pair scientifically for explicit selection,
with SR-1 closed as recorded below; the separate implementation, publication
and vendoring gates remain required. No blocking numerical or
physical inconsistency was identified in the changed equations. This accepts a
bounded source-time approximation and current-stock ET repair; it does not
accept all signed watershed coupling or establish Roads calibration.

Reviewed model source: `631aed1d1c89ed8fa76c5dc3f2e4258a8f199504`. Direct byte
comparison confirms current WATBAL, WATBAL_HOURLY, EVAPPM and SEDOUT source equals
that commit. Independently calculated release SHA256 values:

- Watershed: `53628775e0e97d03f3f8c12e0d99b0f25842efa429d3ce869bf37ee382974461`.
- Hillslope: `080adc9b7b4065f5cba2c2b290369121ea76c042693b74b616ff651117457cd4`.

The tested `src/wepp_hill` exactly matches the dated hillslope executable.

## Findings and conditions

**SR-1 — moderate documentation clarification; closed, no binary change.**
The draft's updated-stock discussion says both callers already apply FIN before
EVAPPM. Hourly WATBAL applies signed exchange, but daily WATBAL allocates only
positive FIN. Negative daily FIN is deliberately not allocated. Describe the
removed adjustment as duplicating *allocated* exchange for hourly signed/daily
positive inputs; for unallocated daily negative FIN, independently debiting the
ET availability estimate is also inconsistent with actual stock. Preserve the
explicit limitation that daily signed coupling remains unresolved. Update the
release explanation and durable contract, without expanding this release into a
new daily withdrawal scheme. Evidence: `src/watbal.for` positive FIN guard and
allocation precede PURK/EVAPPM; `src/watbal_hourly.for` applies signed allocation
before PURK and last-hour ET.

Closure verified against report section 5.1 and the contract
"Updated-stock ET accounting": both now distinguish daily positive-only
allocation, unallocated negative daily FIN, and the open daily signed boundary.
No model changes were made.

**SR-2 — low, provenance wording.** Historical candidate files identify an
uncommitted candidate, and the Cedar semantic summary's descriptive candidate
label still says U1. These are stale labels, not observed numerical mismatches:
source/binary identities and the final equivalence receipt establish the final
candidate. Clarify that chronology in the review packet or release evidence
index; avoid rewriting historical evidence as though it originally described
the dated release.

Disposition: closed by this chronology note and the corrected review packet,
which now links historical provenance to committed source 631aed1d and exact
dated-binary identity. The stale U1 descriptive label is not the authority for
Cedar identity; final equivalence and SHA256 receipts are.

No observed failure justifies changing the accepted numerical thresholds,
clipping negative ET, weakening the inventory guard, or tuning soil inputs.

## Scientific assessment

The local-input correction preserves the original signed sum of local inputs
and routed exchange. Replacing a negative sum with runoff terms alone is not a
valid conservation identity; the traced 38.576 mm omitted local input explains
the inflated withdrawal request. The daily sibling has an actual consumer:
channel subsurface inflow can change the sign before its positive-only allocator.

For the hourly partition let A be incoming surface return on receiving local
area, B=min(A,-F), and L_h the similarly normalized lateral input. Summing
x_h=(F+B)/N+(1-B/A)S_h+L_h yields F+A+sum(L_h). With nonnegative incoming return,
0<=B/A<=1. If A covers -F, no uniform soil debit remains; otherwise the unfunded
remainder remains negative and goes through the existing inventory guard. The
code converts both surface and lateral contributions by upstream local area /
receiving local area. It uses the upstream hourly return array produced by the
preceding element; it does not invent water before that source arrives.

This is a defensible conservative attribution, rather than a unique hydraulic
solution: daily net F does not identify which source actually supplies every
outgoing increment when local storage and several sources coexist. The scheme
chooses incoming saturation return first and uses its hourly support. Intra-day
storage, infiltration and percolation can consequently change. Equal daily
exchange alone cannot prove timing correctness, arbitrary variable-width
geometry behavior, or equivalence to a travel-time solver. The report correctly
states these limits; the unchanged residual guard prevents unsupported net
withdrawal from becoming invented storage.

The ET call order confirms the central correction: both callers reach EVAPPM
with current stock after their allocation and PURK. A second FIN adjustment to
the availability estimate is not a second actual stock update. The root-water
change independently restores the sum of fully rooted layers plus the rooted
fraction of the final layer; substituting surface evaporation water was not that
integral. These shared repairs affect wet and dry states outside Roads. FAO-56
supports relating transpiration stress to rooted available water, but does not
validate this hourly routing attribution or all WEPP coefficients and degenerate
branches. See [FAO-56 Chapter 8](https://www.fao.org/4/X0490E/x0490e0e.htm), checked
2026-10-30.

## Evidence assessed and independent checks

Independently ran from the native checkout:

    PATH=/usr/bin:/bin:$PATH pytest -q tests/test_hourly_return_timing.py tests/test_negative_fin_local_inputs.py
    125 passed in 2.84s

This includes compiled production calculation blocks, conservation/source-support
cases, residual inventory failure, wet/dry FIN independence, root integration,
formatting and the complete 16-year, three-OFE fixture. Log:
`/tmp/wepp261029-independent-science-tests.log`. The broader 663-test gate and
large studies were reviewed from retained artifacts, not rerun by this reviewer.

Reviewed exact-ET trace/parity, lane summary, Roads summary, Disturbed comparison,
Cedar summary/attribution/water audit and final serialization equivalence. The
17 negative timing-only water records and their disappearance after the stock
repair corroborate a causal accounting defect, rather than a tolerance change.
The final Cedar receipt links independently generated native outputs to reused
derived analysis by equality of all non-ELEMENT files; it does not reuse native
PASS execution inputs.

Independently recomputed the maxima across the 96 Disturbed comparisons:
0.7602895531% absolute runoff change and 2.2522522523% sediment change. Roads
reports 96/96 development magnitude passes and no listed physical/accounting
failures. Three climates and four soil textures improve breadth, but fixed
research road-cap coefficients and the FSWEPP2/WEPP2010 comparator do not
establish observed erosion accuracy or validate holdout soils/road geometries.

Cedar full-record volume/sediment/maximum reported peak changes versus 261026 are
-0.41035%, +0.13751%, -0.13860%. The portability control separates its numerical
baseline from the accounting repair; the sediment change versus that control is
-0.52553%. The larger screened event changes remain material: volume
-10.8053% to +1.7918%, peak -10.6767% to +4.2471%, centroid -60.41 to +30.69 minutes.
These overlapping descriptive windows are not independent storms. The changes
are consistent with changed antecedent stock and timing, but this review does
not infer they improve agreement with observations. Finite/nonnegative WAT and
printed discharge consistency are useful gates, not full physical watershed
closure. Preserve these qualifications in published notes and future studies.
