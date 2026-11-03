# Revision 7 full-panel particle flag: independent diagnosis

**Verdict:** the sole failed strict particle predicate is reproduced from the exact revision 4 source case. It is not a newly introduced printed particle-fraction failure. Keep `particle_pass=false`, the 839/840 strict result, and the resulting acceptance veto. This review grants no waiver and changes no tolerance, model, parameterization, or retained evidence.

## Finding and exact comparison

The case is `site / 2711250 / outunrut / paved / low / erosion_road_cap / project`, 2003 day 29. Independent calls to the unchanged [version 2 auditor](audit_particle_closure_v2.py) on both actual `record.json` files return one `fraction_sum` flag each, with 163 EVENT records and 145 positive EVENT records in each full simulation.

All 27 PASS tokens, the audited date/cause, and every fraction/mass value and bound match exactly. The flagged terminal ELEMENT row differs only at zero-based field 11, `Sm`: revision 4 printed `*******`; revision 7 prints `1048.43`. That field is explicitly reported as unavailable in the old audit and is not an operand of the fraction or mass predicates (`audit_particle_closure_v2.py:89–115`). Required `SedLeave` remains `0.000` in both rows.

| Quantity | Both exact outputs |
| --- | ---: |
| Printed fraction sum | 1.000005010000286038 |
| Existing half-last-place fraction bound | 0.0000050050000000015 |
| Excess beyond the strict bound | 5.0002860365e-9 |
| Class mass | 3.124909087608893863656e-7 kg |
| Printed terminal bulk mass | 0 kg |
| Existing mass bound | 0.02155261470825554057500518752 kg |

The mass predicate passes unchanged. A printed zero is not evidence of exactly zero internal sediment mass. The annual export is unchanged at 4.22431247935093 kg/year. Six whole output files differ across the revisions; 19 EVENT records have changed tokens, including 16 with changed particle tokens on other dates. Whole-case parity is therefore explicitly absent.

## Existing arithmetic certificate and its boundary

The retained [U11 arithmetic certificate](fraction-arithmetic-u11-certificate.json) and [exact U12/revision 4 applicability receipt](fraction-arithmetic-u12-applicability.json) identify this exact prior source record, binary, outputs, event, and tokens. I reran both existing Python certificate/checker programs against the retained observations, without a model run or build. Both regenerated JSON objects equal their retained certificates exactly. Their source-record, observer binary, trace, full-period output, retention-manifest, and arithmetic assertions pass.

For the exact observed revision 4 state, sequential binary32 normalization gives native fraction excess `2.727057517697422e-8`, within the operation-derived bound `2.9802335177470655e-7`; the subsequent printed values explain the retained strict failure. This is the existing exact-state explanation, not an added allowance in the audit.

**Coverage limitation:** revision 7 internal class loads, sums, and final fractions were not observed by this review. Identical rounded tokens do not establish identical internal binary32 states. Because whole-case output parity also fails, this review does not transfer the native arithmetic certificate to revision 7. The [existing scientific disposition](fraction-arithmetic-scientific-disposition.md#exact-candidate-applicability-and-provenance) already requires later-candidate applicability evidence. Fresh exact-state evidence would be needed to claim the same internal arithmetic explanation for revision 7; it is not needed to identify this as an already retained output-level strict flag.

## Evidence binding and scope

- Panel declaration SHA256: `68fa8f4507821db21e104a625da0f6ba6401136bc6408594c4051344a51f6b04`.
- Panel results SHA256: `9fb20c75ecccaddfc812ef9e001e1da58ce5543b9f726acd9242f04ce26e7bc3`.
- Exact revision 4 source record SHA256: `6b9ea7170f2cac5b60816894726f07f86c8f6fe37abf478bdc595a8b80c42dd7`.
- Revision 4 watershed binary SHA256: `2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48`.
- Revision 7 watershed binary SHA256: `4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825`.
- [Machine-readable readback](resumption-r7-panel-particle-diagnosis.json) SHA256: `a29c84e957dc3b1e45b5cf68dac09b49cbc20cef0b6bf12da245e6967a5972a9`.

The machine readback retains both flags, their only token difference, complete output bindings, certificate/helper hashes, and the precise limitations. I verified all 12 model inputs against both actual case directories, all 14 ordinary output hashes, the revision 7 auxiliary input and execution logs, and the result-row/record fields. Reviewed input/output/record hashes remained unchanged after the readback. No native run, production edit, or change to a frozen review occurred.

This is a bounded diagnosis of the sole failed particle event. It does not independently re-audit all 840 physical histories, approve the magnitude screen, accept a Roads parameterization, or establish a universal conservation/error bound. The strict failure remains a release/scientific acceptance blocker under the frozen gate.
