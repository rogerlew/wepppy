# Depth-based replacement for the rejected strict material policy

Status: researched proposal, 2026-09-14. The owner rejected strict material
eligibility as non-viable, then authorized this investigation. No production
soil policy, source acquisition or runtime conformance is claimed.

## Findings and correction

NRCS explicitly recognizes H1/H2/H3 as generalized layers retained during
conversion of older State Soil Survey databases into NASIS approved map units.
H is not sufficient evidence of rock or unusable depth. The earlier proposal
missed this guidance; a lack of a modern genetic designation should not have
been used to discard these records.

The [National Soil Survey Handbook, August 2024](https://directives.nrcs.usda.gov/sites/default/files2/1725389663/National%20Soil%20Survey%20Handbook%20%28entire%20handbook%29.pdf),
618.38(C)(2), printed page 51, supplies that evidence. Sections 618.36–39
describe depths and thickness as representative component observations.
Its current combination-horizon instructions require contiguous representative
depths; older Fundamental Query guidance describes coincident paired horizons.
Retaining the date/source distinction matters when interpreting legacy records.

The [NRCS Illustrated Guide to Soil Taxonomy](https://www.nrcs.usda.gov/sites/default/files/2022-06/Illustrated_Guide_to_Soil_Taxonomy.pdf),
“Paralithic Contact,” identifies Cr as soft bedrock. Including Cr in cumulative
recorded material depth is therefore an explicit model-proxy choice, not a claim
that Cr is unconsolidated soil. Original THICK's retained SAS sums recorded
layer depths without a designation filter; it does not resolve which material
each original survey recorded. All-layer inclusion is evaluated as sensitivity.

## Reproducible experiment

Run from the repository root:

    .venv/bin/python docs/work-packages/20260914_staley_m3_integration/artifacts/depth_policy_experiment.py

[Script](depth_policy_experiment.py) and [JSON results](depth_policy_results.json)
retain four counterfactual evaluations using the unchanged offline helper.
Copied research rows represent documented H, and optionally Cr, as ordinary C
to isolate material eligibility; source records are never relabeled or written.
Endpoint candidates suppress `hzthk_r` only in these temporary copies, retaining
the number of source disagreements. This is not a production parser or adapter.

| Candidate | Material and depth interpretation |
| --- | --- |
| strict_v1 | Unchanged rejected production candidate; retained offline baseline |
| h_only | Admit H1/H2/etc.; retain all other offline checks |
| depth_no_r | Admit H and Cr; exclude explicit hard R; use endpoint differences and audit separate thickness disagreement |
| all_recorded | Sum all recorded layers, including R; endpoint differences; sensitivity only |

All four experiments retain stable key checks, positive finite ordered depths,
zero start, continuity and unexplained-overlap rejection. Depth-no-R also
evaluates the bounded legacy combination-pair rule described below.
Unknown/mixed-R material remains
unavailable in `depth_no_r`; this experiment does not prove universal designation
coverage. Missing components and percentages retain offline rules, so these
results isolate material/depth changes, not the proposed above-100-weight policy.

## Measured results

| Source | Strict valid components | H-only valid | Depth-no-R valid | Depth-no-R map units with an estimate |
| --- | ---: | ---: | ---: | ---: |
| Moscow Mountain | 68 / 91 | 68 / 91 | 91 / 91 | 44 / 44 |
| Topanga | 9 / 64 | 12 / 64 | 31 / 64 | 13 / 13 |
| az_ponderosa | 172 / 235 | 175 / 235 | 187 / 235 | 53 / 54 |
| Development cache | 16 / 63 | 45 / 63 | 52 / 63 | 32 / 34 |

The development cache includes keys outside the watershed. Every one of the
watershed's ten keys obtains an estimate under H-only and depth-no-R:
4,311,420 / 4,311,420 cells, versus 8,705 under strict. Both candidates give
163.55344468875683 cm as the equal-cell mean (S = mean / 254), before SBS
intersection. This is thickness availability, not final model Valid coverage,
nor verified SSURGO collection lineage or debris-flow probability.

Depth-no-R leaves 33 Topanga, 46 az_ponderosa and 11 development components
unavailable because they have no horizons. Two az_ponderosa components remain
explicit all-R nonsoil. The unavailable az_ponderosa map unit cannot be repaired
by inventing a zero observation.

Recovering previously omitted components changes some already-available
map-unit means: Moscow Mountain has eight changes (−12.158 to +0.061 cm),
Topanga five (−27.176 to +45.333 cm), and az_ponderosa nine (−9.865 to
+10.746 cm). These are common-key deltas, not basin means. Isolating hard R
by comparing all-recorded against depth-no-R changes 34 az_ponderosa map-unit
means (maximum +155.059 cm), five Topanga means (maximum +25 cm), and none
in Moscow Mountain. Explicit rock treatment
therefore matters beyond coverage.

The live cache contains 16 separate thickness-field disagreements in seven
components; Moscow Mountain has one, the other frozen fixtures none. Endpoint
differences remain the selected quantity; disagreement becomes visible metadata,
not a tolerance-based silent repair. This is a proposed interpretation of
representative fields, not proof that every disagreement is harmless.

## Recommended replacement and limits

Advance `depth_no_r` as the replacement proposal. Include documented H and
weathered Cr with ordinary O/A/E/B/C layers, derive cumulative contiguous
recorded depth from representative endpoints, and exclude explicit terminal R.
Do not reject a whole otherwise usable profile because its separate reported
thickness differs. Preserve both values and disagreement reasons. Retain
errors for nonfinite/reversed depths, unexplained gaps/overlaps, duplicate-key
conflicts and soil reappearing below hard R. No extension to 150/200 cm,
depth extrapolation, root-zone truncation or hydraulic-property requirements.

H eligibility has direct NRCS support. Cr inclusion and thickness-field
disagreement handling are separately visible scientific choices; H-only already
restores this development basin, so neither broader choice is justified merely
by making that basin pass. They recover real recorded profiles in the frozen
panel and approximate cumulative layer-depth semantics while keeping hard R
explicitly separate. This is sensitivity evidence, not calibration validation.

Proposed legacy-pair recognition is bounded: exactly two distinct horizon IDs
within one component, identical positive endpoints, identical combination
designation/name containing `/` or ` and `, both independently admitted material,
and no conflicting stable-ID records. Count that physical interval once and
retain both source records with `legacy_combination_pair` diagnostics. All
other overlap remains unavailable. This is an inference from the two generations
of NRCS guidance; the authentic panel has no pairs. Sixteen analytical cases pass
in the retained script, including a valid named pair, ordinary duplicate ranges,
offset overlaps, gaps, conflicting IDs, R below/within soil, Cr, H and reversed
depths, duplicate conflicts confined to rewritten fields, normalized IDs and
pairs with repeated identical IDs. Pair reductions retain both source IDs,
source-row counts and an explicit diagnostic. Independent review and
production-boundary tests remain required.

Keep usable component normalization and binary cell support as proposed in
the delivery document. Original THICK remains the approved fallback direction,
but acquisition is unapproved; full primary thickness availability here does
not satisfy fallback acceptance or settle survey lineage.

## WEPP isolation evidence and remaining work

The experiment executes the current `Horizon.valid` predicate on raw records
without constructing a Horizon, estimating properties or invoking a builder.
Of 178 live horizon rows, 106 pass that raw predicate. Under depth-no-R all
178 belong to depth-usable components; 72 therefore fail raw WEPP readiness
while belonging to those components. This is a component-membership comparison,
not a count of individually included depth intervals: terminal R may be excluded.
Builder defaults/estimation can change actual WEPP readiness; this does not
replace the required before/after builder-output regression.

No production files, shared soil builders, live project records or offline
defaults were edited. Next: ratify exact Cr/endpoint/pair treatment, validate
analytical edge cases, resolve lineage/delivery and S09, then obtain the final
contract checkpoint reviews. Existing preliminary reviews of the rejected
proposal do not approve this replacement.
