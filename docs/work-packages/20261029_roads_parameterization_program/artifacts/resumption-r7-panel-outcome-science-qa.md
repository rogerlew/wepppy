# Revision 7 full-panel outcome: scientific QA

Reviewer: `mipa_qa`, 2026-11-03 UTC. **Score/artifact readback PASS; scientific
acceptance FAIL.** The frozen conditioned-U12 development replay remains below
both magnitude thresholds and retains one strict particle failure. No tolerance,
parameter, material split or previously frozen artifact was changed by this review.

## Exact results and acceptance

| Population | Passing / declared | Raw fraction | Equal-material fraction | Required overall |
| --- | ---: | ---: | ---: | ---: |
| Meaningful reference above 1 kg/year | 713 / 766 | 93.0809% | 93.0711% | 95% |
| Small reference at or below 1 kg/year | 31 / 74 | 41.8919% | 41.2454% | 95% |

All **840** native calls, existing physical audits and daily completeness audits
pass their respective declared checks. Strict EVENT particle acceptance is
**839/840**. The compound validity gate and both raw/equal-material numerical
gates therefore remain false. The 96 magnitude failures comprise **48 meaningful
underpredictions, five meaningful overpredictions and 43 small-load exceedances**.
The particle-failed case is already among the underpredictions, not an additional
numerical-denominator exclusion.

The meaningful-load 90% major-stratum gate also fails for Denver (84.92%),
outsloped-unrutted design (79.19% equal-material), material 2711184 (70.91%),
material 2711250 (85.19%) and the no-detected-horizon group (85.06% equal-material).
All small-load cases are outsloped-unrutted; their low aggregate success cannot
be excused by the much larger meaningful population. Detailed small-load climate,
surface, traffic, material/restriction and intersection results remain in the
bound score. A no-detected-horizon label is not proof of absent geological
restriction.

Signed bias remains explicit: meaningful cases have 543 exports below their
reference and 223 above, including **11 zero exports with positive meaningful
references**. The positive-only raw/equal-material mean log10 ratios are
-0.241506 / -0.250494; they exclude those 11 zeros. The small-load population has
49 zero references and 22 zero exports, including four positive-reference zero
exports. These counts remain separate; no epsilon replaces a zero denominator.

## Engine comparison and strict particle limit

Compared with the exact frozen r4 inputs/reference baseline, **622 annual exports
are identical and 218 differ**: 80 decrease and 138 increase. Changes range from
-5.73408 to +0.87912 kg/year. Every case changes at least one ordinary output;
5,270 of 5,880 ordinary output files differ. **No case changes its magnitude
pass/fail classification**, so there are zero magnitude recoveries or regressions.
R7 changes modeled responses without resolving this panel's discrepancy classes.
This measures the engine bundle, not isolated FC/HK causality or the effect of
fresh input production.

The sole strict particle failure is
`site / 2711250 / outunrut / paved / low`, on 2003 day 29. Its annual export is
4.22431247935093 kg/year against a 92.2020856462412 kg/year reference, a ratio of
0.0458158. The separate [particle diagnosis](resumption-r7-panel-particle-review.md)
reproduces the same printed fraction-sum failure from the exact r4 source case.
The strict bound is exceeded by approximately 5.000286e-9; the mass predicate
passes. This is an already retained output-level flag, not a new rounded-token
regression. It remains a failed predicate under the frozen acceptance contract.

The old native arithmetic certificate describes the observed r4 internal state.
R7 internal class values were not observed, and whole-case output parity fails.
Identical printed tokens therefore do not transfer that certificate to r7.
Neither this review nor the diagnosis grants a waiver or widens a bound.

## Independent readback method and bindings

The reviewer authored the original scorer, whose implementation was independently
reviewed by `mipa_contract_correctness`. This result review uses a separate
arithmetic reader that **does not import the scorer**, plus direct per-case
classification and r7-minus-r4 arithmetic. No native executable or output
converter was invoked.

The readback verifies exact membership of all 840 declarations/results/baseline
cases, executed review receipt bindings, current frozen scoring dependencies,
all model/auxiliary inputs and execution logs, all **5,880 native output hashes**,
record/audit bindings, and all output hashes of **480 unique FSWEPP references**.
All **840 actual loss reports** were parsed again and exactly match recorded
metrics. Seven source IDs still correspond to seven distinct emitted material
families; no duplicated label increases the material count.

Independent arithmetic reconciles **7,422 major-stratum and intersection groups**,
their raw/equal-material fractions, positive-only signed biases and zero counts.
Each population contains all 57 declared multi-axis combinations. Intersections
remain descriptive; no retrospective 90% rule is added for sparse cells. All
840 case rows retain their outcomes, including the strict particle failure.
Separate direct classification verifies each displayed category and zero
recoveries/regressions. Input and score artifact bindings remain unchanged.

| Evidence | SHA256 |
| --- | --- |
| Panel `results.json` | `9fb20c75ecccaddfc812ef9e001e1da58ce5543b9f726acd9242f04ce26e7bc3` |
| Panel `score.json` | `b9ccda56893dc28967500c0c2c0332be0bce8150e389bb7edcb3d5bbbcd34631` |
| `review_r7_panel_score.py` | `e08745719fc779b28810a9c65e39773d3f56475cc10ae267dd4f8fc5b4ad6d6e` |
| `resumption-r7-panel-score-qa.json` | `a23311756357799a1f1ed1bbff4693b7b86b2348767ee15ec11aac49ead24aa4` |
| `resumption-r7-panel-science-readback.json` | `551499ad34d8555f2ed44f89495effeb9f71bb5e55a1e38931c1691530d08519` |
| Separate particle diagnosis receipt | `a29c84e957dc3b1e45b5cf68dac09b49cbc20cef0b6bf12da245e6967a5972a9` |

The direct readback does not independently rerun every full physical audit or
establish complete water/particle closure. Positive terminal sediment without
EVENT payloads retains the stated audit limitation. This remains development
evidence on conditioned historical soils, not field calibration, withheld
validation, parameter/default adoption, or a human-approved configuration view.
The separate copied-project controller workflow cannot convert these failed
scientific results into acceptance.
