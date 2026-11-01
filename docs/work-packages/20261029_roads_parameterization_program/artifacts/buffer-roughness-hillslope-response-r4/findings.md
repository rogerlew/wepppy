# Buffer roughness persistence: useful response, insufficient remedy

One of seven selected generated-soil benchmark failures recovered the frozen
envelope, and neither passing control regressed. The three primary small-reference
failures remain outside it. Roughness persistence therefore passes the
predeclared selected-panel improvement criterion but is **not a sufficient
remedy or an accepted production parameterization**.

## Scope and evidence

The [plan](../buffer-roughness-hillslope-response-r4-plan.md) ran 36 fresh full
16-year histories: the original nine legacy/generated pairs, with the existing
buffer roughness rule off and on. The panel contains four materials and three
climates; eight cases are outunrut and one is outrut. The generated lane is the
existing U12 `erosion_road_cap` candidate: road Ki/Kr/critical shear use the
matched legacy template, dynamic road conductivity adjustment is disabled,
and upper-200-mm road conductivity is capped to the reference. The existing
[conditioning script](../engineered_surface_screen.py) is unchanged.
This is not a test of unmodified
generated soils or the full Roads matrix.

All 36 runtime, physical and strict-particle checks passed. All 18 off histories
reproduced the seven ordinary R4 files exactly. Nine legacy and three generated
null controls remained exact; six generated histories exercised the rule.
Observed first-two-layer density/porosity and recorded drivers stayed exact in
all 18 pairs. Both independent [scientific](../buffer-roughness-hillslope-response-r4-scientific-acceptance.json)
and [implementation](../buffer-roughness-hillslope-response-r4-u2-implementation-final-readback.json)
readbacks passed. The 44 copied verification passes retained 88 receipts and
left accepted case bytes, sizes, modification times and inventories unchanged.

The original isolated-buffer campaign remains failed. Its separate localization
established native upstream coupling; this study explicitly measures that
whole-hillslope response. Four valid earlier histories stopped for a
[verification ownership risk](../buffer-roughness-hillslope-response-r4-verifier-amendment.md)
remain separate from this fresh 36-history dataset. No canonical native source, release,
default, withheld case or UI was changed.

## Results and residual processes

[All 18 annual comparisons](annual-response.md) are reported without selecting
only improvements. Display values are rounded; [summary.json](summary.json)
retains the exact recorded values and complete annual role budgets.

| Primary contrast | Generated off, kg/year | Generated on, kg/year | Frozen upper bound, kg/year |
| --- | ---: | ---: | ---: |
| B1, Denver paved/high | 7.155468 | 3.836365 | 1 |
| B2, Flagstaff gravel/high | 18.190407 | 13.879884 | 5.603680 |
| B3, Denver gravel/high | 8.146888 | 7.198573 | 1 |

B8 recovered: 378.851861 became 96.728135 kg/year against a 37.2860 kg/year
reference. B4 and B7 remained within the envelope. B5/B6/B9 underpredictions
were unchanged as expected null controls. Legacy B2 remains outside the
FSWEPP2 reference envelope even with its complete legacy profile; R4 legacy
outputs are not replacement acceptance targets.

At all six active generated target events, the native interrill delivery factor
and fraction reached zero. That is an executed source pathway, not an estimate
of its share of the annual reduction. Target-day buffer crust adjustments were
inactive, and the final critical-shear adjustment was not universally increased.
For B8, annual buffer surface outflow changed only from 981.571 to 979.390
m³/year, while its signed annual net sediment addition fell from 337.692 to
56.365 kg/year. This is not evidence for a storage-only explanation or for
gross erosion/deposition quantities.

Residual target events remain informative. With persistence on, B1 and B3
still have zero resolved grid net exchange: outgoing bulk sediment closely
matches the incoming receiving-duration mass. B1's target export actually
increases with its changed upstream supply despite a lower annual export.
B2's positive target grid net exchange becomes zero, but substantial incoming
sediment still leaves the buffer. These are bulk boundary observations, not
tagged origins or proof that no simultaneous subgrid processes occur.

## Next bounded question

First decompose the existing consumed first-two-layer storage observations for
all nine pairs: structural upper limits, saved liquid/ice state, contributing
lengths and snapshot ownership. Retain actual conductivity/minimum-layer
weighting, forcing, runon and time support alongside storage. For B1/B2/B3,
the persistence-on generated connected available storage is about
66.1/39.7/50.8 mm, versus legacy 89.8/72.7/83.5 mm. The three underprediction
controls show the opposite direction. These selected-event contrasts motivate
the question; they do not establish annual causality or a native defect.

Preserve dry-water offsets, coarse-fragment and entrapped-air corrections,
native zero/max branches, and actual computational layer depths in that
decomposition. A consumed saved state is not automatically a common-time
snapshot across OFEs; source writers and observed execution must establish
its ownership. Do not fit a layer depth to force agreement.

Use the retained observations before adding a new native observer. If an actual
snapshot epoch or producer remains unobserved, predeclare only that missing
observation, with the same passing and opposite-direction controls and exact
ordinary-output parity. Preserve the 200 mm soil-boundary contract. Do not fit
another roughness, conductivity or porosity multiplier from these residuals.
Physical validity of the configured roughness and shared routing law remains
open; broader validation and the human UI-specification gate remain outstanding.
