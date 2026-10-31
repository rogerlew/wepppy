# Roads parameterization resumption on artifact revision 3

The native release prerequisite is closed. These studies use final watershed
binary SHA `1d07f5e47692a543e653f449feea23cf298093a9fd664d7a01a1b71dc5e01531`.
No production parameter/default changes, withheld outcomes or UI implementation.

## Final-pair role readback

`role-boundary-assessment-r3.json` rechecks all 840 current cases and 480 unique
FSWEPP2/WEPP2010 references through the Rust ELEMENT reader. Recorded native
hashes and matching climate, slope and management inputs pass. Net exchanges sum
to the outlet difference; these are boundary budgets, not tagged sediment origins.

| Failing group | Cases | Largest difference: road | Fill | Buffer |
| --- | ---: | ---: | ---: | ---: |
| Meaningful high | 5 | 0 | 0 | 5 |
| Meaningful low | 48 | 11 | 19 | 18 |
| Small-reference excess | 43 | 1 | 8 | 34 |

A uniform road-erosion reduction is unsupported. Underprediction is widespread,
while the excess groups mostly differ downstream. This is attribution evidence,
not proof that a particular hydraulic or erosion parameter causes the difference.

The initial adapter stopped because the final score schema stores `export_kg_yr`
and omits the old derived `ratio`. The corrected adapter computes the ratio only
for references above 1 kg/year. No native files, thresholds or completed outputs
were changed; both execution logs are retained.

## Same-engine whole-soil control

Declaration: `legacy-soil-control-r3-declaration.json`. All 96 current misses plus
first passing case per climate/design (20) are retained. Only `p1.sol` changes to
the exact hash-verified reference deck; binary, climate, slope, management, run
file and hourly/PMET/snow sidecars remain unchanged. This is a diagnostic, not an
accepted generated-soil candidate or a proposal to adopt legacy templates.

| Original group | Cases | Control within magnitude criteria |
| --- | ---: | ---: |
| Meaningful high misses | 5 | 4 |
| Meaningful low misses | 48 | 47 |
| Small-reference exceedances | 43 | 28 |
| Meaningful passing controls | 18 | 18 |
| Small passing controls | 2 | 2 |

All 116 native executions complete and pass physical audits. A fresh verification
rehashes every recorded input/output, verifies the sole changed input and recomputes
all native audits. The 116 labels contain 96 distinct consumed-input sets. The control recovers
79/96 misses without losing a passing control. Seventeen residual failures map to
11 distinct consumed-input sets, all outunrut; material aliases do not count as
independent evidence. One original low case becomes a high miss, reinforcing that
recovery counts alone cannot justify a universal correction.

The full generated-soil acceptance matrix remains **713/766 meaningful and 31/74
small passes**, with 840/840 physical passes. The selected control panel does not
replace those denominators or meet the program's acceptance gate.

## Next experiment and rationale

`runtime-bridge-r3-design.json` selects the 11 distinct residuals and one passing
control per climate. Cross hourly mode, PMET and snow sidecar presence: 128 cells,
16 existing all-present controls and 112 new executions. Keep the legacy soil
format and all other inputs exact. PMET absence selects original Penman; snow
absence changes its default threshold. These are causal controls, not calibrated
regional settings or automatic production recommendations.

The revision-2 runtime results remain historical: the native recession repair can
change their conclusions. Resolve this small same-soil engine/runtime bridge
before selecting generated-soil hydraulic parameters. Subsequent contrasts should
isolate role-specific hydraulic/storage effects while preserving generated
materials, erosion properties, 200 mm normalization and restriction provenance.

Legacy soil files are format98.4 and generated profiles format9002. Do not splice
blocks between them or assume conversion is neutral. Any role-wise legacy
substitution first needs demonstrated initialization equivalence. The retained
fixed-site PMET/snow bundle across climates also remains an explicit limitation;
regional runtime and broader geometry validation are still required before
parameterization acceptance. UI specification/layout remains human-gated.

Retention: `revision3-resumption-v1-retention.json` records 3,037 archived files
with every member rehashed. Documentation lint passes; this change adds study
adapters/evidence only and does not alter production behavior.
