# Roads continuation: production versus downstream exchange

Completed 2026-10-31 UTC on the released revision-2 engine. Parameterization
acceptance remains **719/766 meaningful-load and 30/74 small-load comparisons**.
No defaults, native source, criteria, withheld outcomes or UI behavior changed.

## Readback of the complete development panel

`role_boundary_assessment.py` rereads all 840 candidate outputs and 480 unique
FSWEPP2/WEPP2010 references through the canonical Rust ELEMENT reader. Output
hashes, matching climate/management/slope inputs, existing candidate budgets and
net-exchange identities pass. OFEs 1/2/3 are road/fill/buffer for these research
decks. Net exchange is outgoing minus incoming sediment; it is not gross erosion
or tagged particle provenance, and its largest difference does not prove causality.

| Original group | Cases | Road-boundary ratio median, where defined | Both road exports zero | Largest absolute net-exchange difference: road / fill / buffer |
| --- | ---: | --- | ---: | --- |
| Meaningful excessive export | 6 | 0.899, 3 defined ratios | 3 | 0 / 1 / 5 |
| Small-load exceedance | 44 | 0.584, 27 defined ratios | 17 | 1 / 9 / 34 |
| Meaningful underprediction | 41 | 0.202, 25 defined ratios | 16 | 9 / 17 / 15 |

In the six excessive meaningful-load cases, the largest net-exchange difference
is downstream in every case; three produce no road sediment in either model.
For small-load exceedances, downstream net exchange becomes a source in 17/44
modern cases versus 3/44 references. Others can still have net deposition with
less retention than the reference. Uniformly reducing road erodibility would
miss important downstream behavior and worsen existing underprediction.

See [full boundary readback](role-boundary-assessment-v1.json). Ratios omit zero
reference-road exports rather than dividing by an epsilon; all such cases above
have zero candidate-road export as well. Original outlet acceptance denominators
remain unchanged.

## Same-engine whole-profile legacy-soil control

The frozen declaration covers all 91 development misses plus one passing case
per climate/design (20 controls). Replace only consumed `p1.sol` with its verified
legacy reference deck; retain the exact revision-2 executable, climate, geometry,
management, run file and project runtime sidecars. The unconsumed `reference.sol`
copy satisfies the existing audit inventory. All 111 runs complete and pass the
unchanged physical audits. They represent 90 unique consumed input sets; repeated
legacy materials are not independent evidence.

| Original group | Cases | Within original magnitude criterion using control soil |
| --- | ---: | ---: |
| Meaningful excessive export | 6 | 5 |
| Meaningful underprediction | 41 | 40 |
| Small-load exceedance | 44 | 31 |
| Passing controls | 20 | 20 |

Thus 76/91 previously failing comparisons meet the criterion when the soil
profile alone changes. This supports investigating the generated soil treatment;
it does not identify which role, hydraulic property or erosion coefficient causes
the differences. The remaining 15 failures represent nine distinct input sets:
13 small-load exceedances (Denver/Flagstaff), one Charleston case that changes
from low to high, and one still-high site case. Differences between this control
and WEPP2010 include both engine and runtime, not engine alone.

Legacy substitution is **not an accepted modern-soil candidate**. This selected
diagnostic panel cannot establish overall improvement or generalization. See the
[declaration](legacy-soil-control-r2-declaration-v2.json),
[summary](legacy-soil-control-r2-summary.json) and
[paired case values](legacy-soil-control-r2-comparison.json).

## Next experiments

Keep generated material, normalized 200 mm break, deeper horizons and restriction
provenance. First separate fill/buffer erosion coefficients from hydraulics:
compare bounded role-specific coefficient treatments, holding generated hydraulic
profiles and road parameters fixed. Match every arm to the unchanged current
candidate and same-engine legacy control. Declare supported coefficient semantics
and ranges before execution; use legacy values as diagnostic anchors, not proof
that they are suitable defaults for generated soils.

In parallel study design, isolate the nine residual legacy-control input sets
with explicit hourly-mode and climate-runtime controls. Fixed site sidecars across
climates remain a known controlled sensitivity limitation. Do not invent a native
defect from a reference mismatch or tune soils to hide a runtime mismatch. These
checks precede another full development panel, withheld-material validation,
geometry stress, disposable production-project validation and the human UI gate.

## Reproducibility and failed harness lanes

Run the readback with `wctl exec -T weppcloud /opt/venv/bin/python` followed by
`docs/work-packages/20261029_roads_parameterization_program/artifacts/role_boundary_assessment.py`.
The control helper declares a fresh root with `--declare`, then executes without
that option; existing study roots intentionally refuse reuse. Its exact executed
script and declarations are retained with the raw runs. `summarize_role_control.py`
reproduces the compact paired comparison from hash-verified results.

The initial text-splitting prototype could not read joined legacy fixed-width
columns; the completed readback uses the owned Rust reader. An initial selection
assumption requiring a meaningful passing control in every climate/design failed
before native execution; the declaration instead allows any existing passing case.
Control lane v1 omitted the audit's required, unconsumed reference copy and failed
inventory validation after successful native execution. Lane v2 restores that
copy and reruns all 111 cases in a fresh root; no native code or physical tolerance
changed. Failed artifacts and logs are retained, not relabeled as successful.

The [verified archive](role-attribution-archive-v1.json) retains all 3,346 consumed
input/output/evidence files, including the failed harness lane. Every member hash
was read back successfully. Existing source/reference studies remain immutable.
