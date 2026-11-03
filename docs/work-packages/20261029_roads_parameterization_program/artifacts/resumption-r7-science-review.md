# Revision 7 resumption: independent scientific design review

Reviewer: `mipa_qa`, 2026-11-03 UTC. Independent AI review of the declared
experiment and retained evidence; this is not institutional peer review or
validation of unexecuted results. Active plan: `prompts/active/program_execplan.md`.

## Disposition and concrete findings

**Final pre-execution PASS for the bounded 36-call seed trial and exact v3
declaration identified below.** Independent helper, test and staging readback
closes the initial conditions. Native runtime and scientific result gates remain
to be evaluated after execution. No native run was executed by this reviewer.
No r7 Roads score, parameter acceptance, production adoption, or UI approval
follows from this review.

| ID | Finding | Disposition |
| --- | --- | --- |
| R7-S01 | The first current declaration did not explicitly identify the conditioned development soil treatment. | Closed: protocol and ledger v24 now name conditioned U12 `erosion_road_cap`, including legacy road Ki/Kr/critical shear, disabled dynamic road conductivity adjustment, and the upper-200-mm conductivity cap. This is not unmodified generated soil. |
| R7-S02 | All 18 staged v1 modern tasks omit `reference.sol`: the driver took `auxiliary_inputs` from upstream records where that map is empty. The retained u2 rows bind this file, and the reused `continuation.audit` / `analyze.validate_runtime` requires it. Every modern run would fail the audit after execution. | Closed: the driver binds, verifies and copies auxiliary inputs from the retained mode-0 folder and checks them after execution. Independent v3 readback verifies all 36 auxiliary references. V1 and failed v2 staging remain unexecuted. The historical auditor is unchanged. |
| R7-S03 | The reused runtime audit explicitly checked only the UI banner; presence/hash checks alone do not demonstrate consumption of every enabled companion. | Source correction accepted: v2 requires UI, groundwater and PMET stdout markers. Snow's selected native open/read path is confirmed, but no dynamic read trace or stdout marker is claimed. Runtime marker results remain to be observed. |
| R7-S04 | The independent implementation review found that a header-only PASS could satisfy the historical particle checker with zero checked events. | Closed for the declared completeness scope: the independently reviewed helper requires the full PASS daily calendar, accepts sparse/empty ELEMENT, and records positive terminal dates without EVENT payloads. Fifteen tests and all 18 retained histories pass. Native classification does not require EVENT merely because sediment is positive; strict EVENT numerical predicates remain unchanged. |

Reviewed original machine declaration, retained as rejected unexecuted staging:
`/wc1/runs/ro/roads-parameterization-program-20261103/engine-seeds-v1/declaration.json`,
SHA256 `6cf343c22b48f648349903952d847d1e3182bc21453a41b13b86bebe98d001e6`.
All 36 output directories were empty and no execution-start receipt existed at
review. That declaration binds the original protocol, frozen acceptance document,
driver, auditor dependencies, binaries, source panel, and FSWEPP reference records.
The first correction targeted `engine-seeds-v2`, whose staging failed because a
host-prefixed source path was absent inside the service container. That partial
attempt is retained. Explicit path mapping and final source/helper bindings are
in fresh v3. This review does not authorize executing rejected v1 or partial v2.

## Comparability and controls

The proposed 36 calls are nine retained pairs × legacy/conditioned-generated
lanes × r4/r7 engines, using ordinary mode 0 and each complete 16-year history.
They preserve three primary small-reference failures, two passing controls,
one meaningful overprediction, and three meaningful underpredictions. This is
an informative diagnostic subset: four material IDs, three climates, eight
outunrut cases and one outrut case. It does not cover the full acceptance panel.

Independent source readback verified all 432 model-input hashes and 36 auxiliary
hashes across the retained 36 mode-0/mode-1 histories, plus all 126 ordinary
mode-0 output hashes against their prior r4 references. Only `p1.sol` differs
between legacy/generated lanes within each selected pair; climate, management,
geometry and the other model inputs match. Mode-0/mode-1 model-input maps are
identical within each lane. The source results hash is
`c9e9e6d693e5cb917bfd83751122264509f5b2081885471e697094f065e912b9`.

The rejected v1 staging has 36 distinct case/lane/revision tasks and 450 verified files:
432 model inputs plus only 18 auxiliary references, exposing R7-S02. Final v3
binds 468 entries: 432 model inputs plus 36 auxiliary references. Every
engine pair has identical model-input bytes and no experimental controls copied.
Eight unique FSWEPP reference records serve the nine contrasts; QA verified
their 56 output hashes, reference exports, and exact climate/management/geometry
input matches. Repeated references or material labels are not independent data.
The r4 legacy-soil lane remains an engine/material control, not a replacement
acceptance target; its own mismatch with FSWEPP cannot be erased by relabeling it.

## Revision, mode, and causal scope

QA independently extracted the r4 watershed executable from WEPPpy `a5c40031a`:
ELF SHA256 `2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48`.
The staged/installed r7 watershed hash is
`4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825`.
Installed sidecars identify revision 7 and native source
`e0abe0581f77c6f66917e90daf8f8f429e9315c8`; the canonical native checkout is at
release `547b9e7eb`, on the declared default branch. Using both watershed-role
executables in hillslope mode matches the historical execution role.

Historical mode 1 is a private source intervention for roughness persistence.
Inventorying its 18 histories preserves the original contrasts; copying its
control file into release r7 would not execute that intervention. Any future
mode-1 port needs a separately reviewed source lane and ordinary-output controls.
Its historical improvement criterion cannot be reused as r7 parameter acceptance.

The r6 FC/HK correction makes old heterogeneous r4 histories relevant controls,
not current-engine mechanism evidence. The retained r4 arithmetic and observed
states remain valid historical observations. Saved liquid water, percolation and
subsequent routing may change under corrected ownership; selected-event storage
contrasts cannot establish the annual cause of sediment failures. This experiment
measures the total r4-to-r7 engine difference, including intervening repairs.
It cannot isolate FC/HK causality without separate attribution evidence.

Preserving exact inputs separates engine effects from later producer repairs.
Fresh complete preparation must remain a separate declared experiment, with
actual emitted fields, runtime companions and downstream readers checked. The
earlier partial-project omission that changed 433/504 outputs is a concrete
reason not to substitute selective preparation for the configured workflow.

## Frozen criteria and interpretation gates

The predecessor v23 hash matches v24. Historical scores remain **713/766 meaningful
and 31/74 small-load passes**: 744 passes and 96 failures, all on r4. They are not
r7 scores. No withheld outcomes were used in this review.

The machine declaration binds unchanged `acceptance.md` SHA256
`16d6980c4188ea511540cd63161af852c6a7d164856f07665224b8cb8d3f2db4`.
The driver retains the exact meaningful threshold (reference >1 kg/year),
0.1–10 ratio gate, and separate small-load upper bound
`max(1 kg/year, 10 * reference)`. Seed success is comparability, not the 95%
overall / 90% per-stratum development or withheld-validation gate.

Before expansion, require all declared histories and r4 ordinary-output parity,
complete calendars, finite water and nonnegative sediment boundary fluxes,
unchanged strict particle predicates, accounting reconciliation, and explicit
diagnostic unavailability. Existing arithmetic certificates do not clear new
flags. Report signed changes, recoveries and regressions for both discrepancy
directions; preserve common observable definitions and identify new output fields
as unavailable in older versions rather than inventing zeros. The profile's
terminal delivery is not a routed watershed outlet.

A later full 840-panel declaration must retain original references and material
weighting, all major strata and intersections, signed bias, and failed cases.
Fresh preparation, six withheld materials, source-supported physical hypotheses,
and the explicit human configuration specification/layout gate remain separate.
No surface-armor, retention, porosity, conductivity or roughness adjustment is
accepted by the proposed engine replay.

## Final helper and v3 prelaunch readback

Accepted declaration:
`/wc1/runs/ro/roads-parameterization-program-20261103/engine-seeds-v3/declaration.json`,
SHA256 `c60b95c568980858c2b8f0fd0c6e0cf646900c73c0ca0f91bfc711007dbd384f`.
QA independently rehashed all 468 staged input/auxiliary entries, both binaries
and all 78 dependencies. Each of the 18 r4/r7 pairs has identical inputs; all
36 output directories were empty and no execution-start receipt existed at
readback. Declared UID/GID are 1000/993, with four workers and 300-second timeouts.

Independent canonical test command:

```sh
wctl run-pytest tests/tools/test_roads_pass_completeness_r7.py --maxfail=1
```

Result: **15 passed**. Tests cover complete zero-event histories in ordinary and
leap years, empty/sparse ELEMENT, complete positive events, explicit positive
non-EVENT diagnostics, truncated/header-only PASS, missing dates, duplicate and
out-of-calendar dates, missing SRC3 payloads, and changed climate/output hashes.

Independent read-only execution of the helper on all 18 retained ordinary
histories accepts **105,192 daily PASS records**. It preserves **31 positive
terminal non-EVENT dates across eight histories**, and accepts three histories
with no positive terminal sediment. ELEMENT is event-supported, not a daily
calendar. Requiring daily ELEMENT or positive sediment to imply EVENT would
incorrectly reject these retained histories.
The retained `resumption-r7-pass-completeness-readback.json` has SHA256
`b2a8b17711525e1dccb19beffd73ddfa0cadc09482f6ca16a12db94109d7c1b9`;
its counts and helper identity agree with the independent readback.

Both r4 `b01a739957bef5aacf35b4a89bc13eddc9d94804` and r7
`e0abe0581f77c6f66917e90daf8f8f429e9315c8` source use
`runoff(nplane).ge.0.001` meters to select EVENT in `src/wshpas.for`.
SUBEVENT/NO EVENT therefore need not mean zero ELEMENT sediment. The helper
retains date, label, printed sediment and runoff tokens for those cases and
explicitly leaves their particle closure uncertified. This is a completeness
repair, not a new transport tolerance or full mass-closure claim.

The interpreter binds the summary to the results hash, reconciles its acceptance
flag with all row-level physical/particle/completeness and r4 parity predicates,
and checks all three OFEs before paired differences. Failed gates are explicitly
`diagnostic_only_gate_failed`; they cannot be presented as accepted seeds. Its
positive-only log-ratio summary reports excluded zero counts and remains a
selected-panel diagnostic, not the full stratified acceptance calculation.

| Independently reviewed artifact | SHA256 |
| --- | --- |
| `audit_pass_completeness_r7.py` | `187f25c351f96c33b8704aea8d0d11306105f68bd18bb3ad8ff4fd81614484aa` |
| `tests/tools/test_roads_pass_completeness_r7.py` | `69a026f7566611913ae6eb37080996b23b6ae1d26883f67e31eb4da036e526cf` |
| `interpret_r7_seeds.py` | `7e398d4660b17da79a4f21af053a42b448538e3217949650f8e9e772853b1f55` |

No blocking finding remains for executing the declared seed batch. Interpretation,
broader expansion, fresh preparation, candidate selection and the human UI gate
retain the conditions above. The reviewer modified only this review artifact.
