# Revision 7 Roads resumption implementation review

Reviewer: independent `mipa_contract_correctness`, 2026-11-03. Scope: the
pre-execution seed driver, declaration, runtime/physical/particle auditors and
staged artifacts. No native model was invoked; no retained source, input, output
or production file was changed by this reviewer.

## Initial verdict

**HOLD before native execution.** Two reproducible audit integration defects
require correction and an additive declaration amendment. The declared fixed-input
experiment and its separation from current production preparation are otherwise
consistent with the resumption protocol. This review does not approve scientific
acceptance, parameter promotion or UI implementation.

Reviewed driver SHA256:
`38e9bd49e00a7756fe1c8448ee119cabaebb5228d979775afb1170f5f85c9240`.
Original declaration:
`/wc1/runs/ro/roads-parameterization-program-20261103/engine-seeds-v1/declaration.json`,
SHA256 `6cf343c22b48f648349903952d847d1e3182bc21453a41b13b86bebe98d001e6`.
Preserve these bytes as the initial declaration rather than rewriting their
provenance after correction.

## Findings

| ID | Severity | Evidence and consequence | Required disposition |
| --- | --- | --- | --- |
| R7-IMP-01 | High, execution blocker | `rebaseline_r7_seeds.py:148` calls `common.c.audit`, whose runtime validator in `20261029_roads_drainage_validation/artifacts/analyze.py:27` unconditionally requires `reference.sol`. All 18 modern executions declare no auxiliary inputs and stage no such file. A successful native call therefore raises `ValueError('Unrecorded working-directory file')` before its record is saved. | Preserve the declared model inputs. Adapt runtime validation to the explicit auxiliary-input manifest, or stage a separately proven unconsumed auxiliary artifact. Keep exact directory membership, input hashes and native UI activation checks. Test both populated and absent auxiliary states. |
| R7-IMP-02 | Medium, false particle acceptance | `audit_particle_closure_v2.py:audit` validates only encountered EVENT rows and returns `passed=True, structure_valid=True` when none exist. It does not require complete PASS dates or coverage of positive terminal ELEMENT sediment. The physical audit does not read PASS. On a temporary copy of a retained 7.155468077267901 kg/year case, truncating PASS to its three header lines and updating the temporary record hash produced `events=0, passed=True`. | Add a scoped completeness gate using the frozen full climate calendar and positive terminal ELEMENT event coverage. Preserve valid zero-event histories and all existing numeric tolerances. Reject missing/truncated PASS records before seed comparability can pass. |

Both reproductions used temporary copied data only. The first executed the actual
runtime-validator function with a synthetic UI banner solely to reach its file-set
predicate. The second executed the actual particle auditor on copied native
outputs. No result from those probes is model evidence.

## Verified declaration and staging

- All 36 task destinations are unique; there are nine legacy and nine modern
  cases for each of r4 and r7. Every destination output directory was empty.
- Independently rehashed all 432 staged model-input copies against their source
  records. Each staged input is a regular file with a different inode from the
  retained source. All 18 r4/r7 pairs have identical 12-file model-input manifests.
- Rehashed source records and all seven retained ordinary outputs; verified the
  frozen FSWEPP reference records/outputs and matching climate, management and
  slope inputs. Both executable hashes match the declaration.
- r4 is the historical watershed executable
  `2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48`.
  r7 is the watershed executable
  `4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825`.
  Its current sidecar identifies revision 7, source
  `e0abe0581f77c6f66917e90daf8f8f429e9315c8` and the canonical native branch;
  the sidecar SHA256 is
  `6a3ae6193cad7a8d5cb75b1387289a2bf8606ed86f8b7ce26766d4a0b7dfd5a7`.
- Every declared dependency was present and matched its hash, including the
  installed Rust reader extension. The declaration records UID 1000/GID 993,
  four workers and a 300-second per-call timeout. Actual execution identity must
  still match that declaration when the batch starts.
- Mode-1 observation/control files are absent from staged run directories.
  The 18 retained intervention histories remain inventory only. The seed inputs
  contain 17 distinct complete model-input signatures across 18 selected cases;
  case labels must not be counted as independent evidence.

## Acceptance limits

The existing water auditor checks complete daily/OFE keys, finite audited values,
geometry/area agreement and surface/lateral transfer reconciliation. Its retained
apparent soil residual is explicitly not complete water closure. Sediment/EBE
reconciliation and strict particle flags remain separate predicates; a seed pass
must not be described as universal physical validity.

The driver computes the frozen meaningful/small-load classifications, but the
36 selected runs cannot establish the 840-case magnitude gate. The engine-only
comparison preserves the conditioned U12 treatment and historical runtime bundle;
it does not establish current full-preparation behavior or parameter acceptance.
Any native, parser or audit exception must remain a failed/incomplete declared case,
with preserved outputs/logs and no reduced denominator or implicit retry.

## Final readback

### Source corrections and bounded helper repair

The parent corrected R7-IMP-01 by binding `reference.sol` to the retained u2
mode-0 row and copying that verified auxiliary file into every v2 directory.
All 12 model inputs remain sourced from their original records. The driver now
requires the declared UID/GID at launch and native UI, groundwater and PMET
markers. It writes an attributable `native-receipt.json` before parsing/auditing;
an audit exception therefore retains the native result but cannot pass the gate.
Such exceptions remain failed/incomplete cases in the declared denominator of 36.

Under explicit parent authorization, this reviewer authored the scoped
`audit_pass_completeness_r7.py` helper and
`tests/tools/test_roads_pass_completeness_r7.py`. Independent QA must approve
that repair; this review does not self-approve its authored code. The helper API
is `audit(record_path, climate)`, using the frozen climate manifest entry. It
binds the actual climate and ordinary outputs, requires each full-period PASS
date exactly once, validates daily record/trailer shape, and covers every
positive terminal ELEMENT date. Existing EVENT particle arithmetic is unchanged.

Two implementation assumptions were corrected during retained-output readback:

- ELEMENT is sparse and must lie within the climate period; it is not a daily
  calendar. The complete daily requirement applies to PASS.
- Positive terminal sediment does not imply an EVENT record. Selected native
  `src/wshpas.for:161` emits EVENT only for `runoff(nplane).ge.0.001` (meters),
  otherwise writing SUBEVENT/NO EVENT at lines 250–286. Requiring EVENT for all
  positive sediment would add an invalid gate. The helper instead retains every
  positive non-EVENT date, label, runoff and SedLeave token as an explicit
  coverage limitation. Existing strict EVENT criteria certify only those EVENT
  payloads; they do not certify all positive sediment dates.

The writer was compared byte-for-byte to source commit
`e0abe0581f77c6f66917e90daf8f8f429e9315c8`; SHA256
`64b894bd2fcbde426d0714f64ec145117cea656eec115314b95a32e48a5709a8`.
The helper certificate records that source reference without changing any native
threshold, parameter, formula or retained output.

Validation: `wctl run-pytest tests/tools/test_roads_pass_completeness_r7.py -q`
passed **15 tests**, including three truncation depths, year 1/non-leap and year
2000/leap zero-event histories, sparse ELEMENT, positive non-EVENT disclosure,
missing positive dates, duplicate/out-of-period dates, missing SRC3, and changed
input/output bindings. Tests execute no native model.

Read-only application to all 18 retained mode-0 source records passed:
105,192 daily records, 1,677 EVENT records and 753 positive terminal dates.
Thirty-one positive terminal dates across eight cases have no EVENT payload;
their printed runoff depths range from 0.003 to 0.958 mm. The full per-record
certificates and tokens are retained in
`resumption-r7-pass-completeness-readback.json`, SHA256
`b2a8b17711525e1dccb19beffd73ddfa0cadc09482f6ca16a12db94109d7c1b9`.
Helper SHA256:
`187f25c351f96c33b8704aea8d0d11306105f68bd18bb3ad8ff4fd81614484aa`.

### Final v3 declaration and verdict

V2 staging failed before declaration or native invocation because its retained
auxiliary folder used the host `/home/workdir/wepppy` prefix. The driver maps this
known prefix to the existing `/workdir/wepppy` Compose mount and still verifies
every retained hash. Partial v2 staging is preserved; v3 is the executable attempt.

Independent final readback verified
`/wc1/runs/ro/roads-parameterization-program-20261103/engine-seeds-v3/declaration.json`,
SHA256 `c60b95c568980858c2b8f0fd0c6e0cf646900c73c0ca0f91bfc711007dbd384f`:

- 36 unique tasks, 432 model-input copies and all 36 auxiliary references match
  their retained hashes. Every copy is a separate regular file; all 18 r4/r7
  pairs have identical model and auxiliary inputs.
- All 78 dependency hashes, source-panel identity, source/reference records and
  outputs, reference exports, climate/management/slope matches and both binary
  identities match. No execution-start receipt exists; all outputs remain empty.
- The executed driver equals the reviewed source, SHA256
  `0ca275e22d43df6cb2e7c6f50c0aca10fa70925d16a8599abd91ba2123e87d1f`.
  The declaration binds the final helper hash above and UID 1000/GID 993.
- The final gate requires all 36 native, physical, particle and PASS completeness
  checks plus all 18 exact r4 ordinary-output reproductions. Structural exceptions
  preserve the pre-audit native receipt and cannot silently lower a denominator.

**Implementation/staging PASS for this exact v3 declaration, conditional only
on independent QA approval of the helper authored by this reviewer.** Both
initial implementation findings are corrected. There are no other outstanding
implementation blockers for the bounded seed trial. This reviewer ran no native
model and makes no r7 output, score, full physical validity, exact r4 reproduction
or parameter-acceptance claim. Those remain post-execution gates. In particular,
the reported 31 non-EVENT positive dates remain an explicit particle-coverage
limit, and snow consumption has no dynamic read trace in this seed protocol.
