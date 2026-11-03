# Revision 7 seed results and development-panel scientific review

Reviewer: `mipa_qa`, 2026-11-03 UTC. This additive review leaves the frozen
prelaunch review and declarations unchanged. The reviewer did not invoke WEPP.

## Disposition

**Seed comparability and scientific design for the declared 840-case replay:
PASS.** Execute only after the independent implementation review and additive
execution receipt bind the exact declaration, scorer, restriction metadata,
acceptance document, reviews and launcher. This conclusion authorizes a bounded
development comparison; it does not accept parameters, claim withheld performance,
approve production defaults or clear the human configuration specification gate.

The scorer was authored by this reviewer at the parent's explicit request. Its
implementation therefore requires the separate correctness review; the scientific
criteria assessment here is not independent approval of the reviewer's own code.

## Independent seed evidence and interpretation

Reviewed `engine-seeds-v3` under
`/wc1/runs/ro/roads-parameterization-program-20261103/`. Exact bindings:

| Artifact | SHA256 |
| --- | --- |
| `declaration.json` | `c60b95c568980858c2b8f0fd0c6e0cf646900c73c0ca0f91bfc711007dbd384f` |
| `results.json` | `a649bea9c8504744128f2d791ca5992b0ea40c10aa356130412bff43e56c47be` |
| `interpretation.json` | `b36cebb1aee2bbf397781161d78fc1bb869c025971896c95d550d1b0d6669168` |

QA independently rehashed every case's inputs, auxiliaries and all 252 ordinary
outputs; checked physical/runtime flags and audit certificate bindings; parsed
the actual loss reports again; and recomputed the 18 paired water and sediment
deltas from verified audit data. All 36 declared histories pass native, physical,
strict EVENT and daily PASS completeness gates. All 18 r4 cases reproduce their
seven historical ordinary outputs byte for byte. R7 changes 116 of 126 ordinary
outputs. The independent implementation reviewer additionally reran all physical,
particle and completeness audits without changing accepted evidence, as recorded
in `resumption-r7-result-expansion-review.md`.

All nine conditioned-generated seed cases retain exactly their r4 annual sediment
exports and magnitude classifications. Their water diagnostics change, so this is
not evidence that the entire modern simulation is unchanged. Six legacy-soil
controls decrease annual sediment export; all nine legacy classifications remain
unchanged. Both discrepancy directions and the small-load failures persist in the
selected sample. Lower export alone is not evidence of physical improvement.
The selected nine contrasts are not a representative estimate of the 840-case
success fraction and cannot replace its stratified evaluation.

R4 reports 31 positive terminal dates without EVENT payloads; r7 reports 26.
Those dates remain explicit diagnostics outside strict EVENT particle closure.
The native 1-mm runoff classification threshold explains why positive ELEMENT
sediment need not have an EVENT payload. Neither a new particle tolerance nor
complete water/mass closure is inferred. Snow input hashes and its selected
source read path are known; no dynamic snow-consumption trace is claimed.

## Expansion comparability and frozen criteria

Reviewed `resumption-r7-panel-protocol.md`, SHA256
`7799810d4c7f84c9c82a10b2971b1330dcbe32716497aa06ad42d8642edaf958`,
and `panel840-v1/declaration.json`, SHA256
`68fa8f4507821db21e104a625da0f6ba6401136bc6408594c4051344a51f6b04`.
The separate implementation staging review verifies every native input,
auxiliary, source/reference output, binary and dependency before invocation.

The exact source is the conditioned U12 `erosion_road_cap` development panel:
five climates, seven source materials, four road designs, two surfaces and three
traffic levels. Conditioning retains legacy road erosion parameters, disables
dynamic road conductivity adjustment and caps upper-200-mm road conductivity.
It is not unmodified generated soil. The 840 cases preserve their full periods,
FSWEPP reference quantities, geometry, contributing area and ordinary mode 0.
Historical mode 1 is a separate private source intervention and is not ported
by this replay. R4-to-r7 effects represent the engine bundle, not isolated FC/HK
causal attribution. Terminal profile export is not routed watershed-outlet yield.

The frozen `acceptance.md` remains SHA256
`16d6980c4188ea511540cd63161af852c6a7d164856f07665224b8cb8d3f2db4`.
Meaningful references exceed 1 kg/year and require ratios within 0.1–10. Small
references use the exact upper bound `max(1 kg/year, 10 * reference)` without a
lower bound or epsilon division. The 95% overall and 90% major-stratum gates
apply separately to both populations where present. All declared cases remain
in denominators, including failed execution. Physical/runtime/completeness
failures veto acceptance regardless of numeric agreement.

Equal weighting applies to emitted material families across all matched panel
contexts, excluding only identifying SLID labels. This implements the original
rule that duplicated labels do not create independent materials. The actual
frozen panel has **seven distinct families for seven source material IDs**, so
this grouping does not collapse or change its material membership. Raw counts,
source-ID soil strata, emitted soil signatures and exact input aliases remain
visible. Restriction groups use frozen provenance; `no_detected_horizon` is not
proof that a geological restriction is absent.

All climate, design, surface, traffic, source-soil and restriction strata receive
explicit results. All 57 multi-axis combinations are reported descriptively;
the frozen contract does not impose a new 90% threshold on every sparse
intersection. Signed positive-only log-ratio summaries identify omitted zero
references, zero exports and unavailable exports separately. Individual failures,
recoveries, regressions, signed r4/reference differences and worst cases remain
available. Historical 744/840 passes and 96 failures remain r4 results until the
complete r7 panel is executed and independently reviewed.

## Scorer delivery and residual limits

`score_r7_panel.py` is separate from all model drivers and writes scores by
exclusive creation. It checks the 840-case Cartesian membership, source panel,
results/summary, binary, references, diagnostics, inputs, outputs and audit
certificates. The executed review receipt must match its verification receipt
and panel declaration; current scorer, restriction metadata and acceptance bytes
must match exact service-path bindings in that receipt. The implementation
review's R7-SCORE-01 correction is covered by focused drift tests.

| Authored scoring artifact | SHA256 |
| --- | --- |
| `score_r7_panel.py` | `32a7b7a4acffb0acc124014548cb30b7d75e379d0162c3e34ffb240f4585791e` |
| `tests/tools/test_roads_r7_panel_score.py` | `ac4a5723bf66c5e14b25b53cf77c7d4ce3498129670d4377bd3e8eb89188e9b0` |

Canonical validation: `wctl run-pytest tests/tools/test_roads_r7_panel_score.py
--maxfail=1`: **28 passed**. Coverage includes threshold equality, zero/nonfinite
exports, unequal material multiplicity, exact membership, failed-case denominators,
physical veto, sparse intersection reporting, label aliases and post-freeze
receipt/declaration/scorer/metadata/acceptance drift. This is scorer validation,
not native execution or scientific validation of the unexecuted 840 outcomes.

No blocking scientific design finding remains for this fixed-input replay.
Complete current production preparation, actual project routing/readers, the six
withheld materials, justified physical parameterization, and human configuration
review remain separate gates. The scorer always reports final scientific
acceptance as false. Audit predicates and positive-only bias diagnostics retain
their stated limits; they cannot establish field calibration or complete closure.
The bounded scorer is deliberately local to this frozen panel. Any reuse for a
different panel requires explicit membership, provenance and criterion review.
