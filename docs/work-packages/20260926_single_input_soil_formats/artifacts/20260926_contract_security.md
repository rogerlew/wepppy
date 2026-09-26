# SUDI-02 independent contract security review

## Findings and disposition

| ID | Severity | Surface and evidence | Required action | Status |
| --- | --- | --- | --- | --- |
| CS-01 | Medium | Native text-token interpretation. Python `shlex.split` accepts `soil / 1 0.2 0.6 1000 0.01 2` as eight fields with one layer. A direct gfortran list-directed-read probe returns success while leaving the layer count and saturation unassigned. `input.for` uses this read form for soil headers. Python also changes a native doubled-apostrophe label (`'O''Brien'`) to `OBrien`. | Specify native-compatible token syntax, rejecting ambiguous punctuation, unsupported quoting and escapes before publication; retain direct hostile-label and valid-label regression evidence. | Resolved in contract: Upload interface and validation now requires unambiguous native token syntax. Implementation evidence remains required at final review. |
| CS-02 | Medium | Accepted comments can interrupt native records. `input.for` does not call `eatcom` between the 9002 adjustment header and soil header, or immediately before restrictive records. The existing upload validator filters comments while the derived-copy writer retains them. | Normalize standalone comments/blanks out of derived soil records while preserving accepted source bytes; place generated provenance only where the native reader skips comments. Test valid interspersed comments through native preparation/execution. | Resolved in contract: derived-copy and provenance placement rules now explicitly cover these gaps. Implementation evidence remains required at final review. |

No unresolved medium/high contract findings. No risk acceptance was used.

## Metadata and scope

- Reviewer: `/root/soil_format_contract_security`, independent security reviewer.
- Date: 2026-09-26 UTC.
- Starting implementation revision: `64dc33a0d`; production files remained unchanged during this review.
- Reviewed: SUDI-02 checkpoint and active ExecPlan; `docs/schemas/single-user-defined-inputs-contract.md`; ADR-0075 amendment; existing strict validator, source lifecycle and WSU parser/writer.
- Native evidence: `/workdir/wepp-forest/src/input.for`, `infile.for`, `infpar.for`, `eatcom.for`, and the pinned release source `f24c957e3633898e0fd4cbbea5ae08c781f29dba`. The working native checkout differs in unrelated watershed handling and excess-layer cursor handling; the reviewed record layouts and adjustment logic match the pinned source.
- This is a pre-implementation contract review, not final security/correctness/QA approval or deployment authorization.

## Security triage and threat model

Security impact is **high** because the authenticated upload boundary admits additional untrusted records that reach a native executable. A dedicated final security review is required after correctness and QA review.

An authorized project user may upload malicious, malformed or unexpectedly encoded soil bytes. Existing project authorization, opt-in policy, multipart limits, source hashing, descriptor-relative publication, locking and archive/fork coordination remain mandatory. Expanding formats grants no filesystem references, shell interpretation, external fetch, new dependency, queue topology or authority.

Native list-directed reads are the interpretation boundary: Python parse success cannot establish safe native interpretation. Count limits, full record consumption, ASCII numeric syntax, finite native-representable values and native-compatible labels must apply before publication and again to generated inputs. Version-specific schemas prevent missing records from consuming the following OFE.

## Contract assessment

The native reader confirms nine soil-header fields for both 2006 and 2006.2, six values per layer, and the three-field anisotropy/restrictive-conductivity record. The 9002 layout comprises the five-field adjustment header, eight soil-header fields, eleven base layer values plus seven hydraulic values, and the three-field bedrock record.

The proposed upload-only preservation path is appropriate: it retains version, `avke`, `ksflag`, restrictive values and supplied 9002 hydraulics while leaving ordinary catalog/Disturbed serialization unchanged. Native 9002 behavior remains explicitly supplied model input; WEPPcloud does not infer a Disturbed class. The explicit modifier exception for a `developed` label prevents an uploaded display label from suppressing a requested conductivity modifier.

The state matrix covers absent/empty source, existing 7778 source, populated new versions, reuse, rejected replacement, malformed/missing populated source and archive/restore. The amendment retains independent landuse/soil modes and all non-buffer OFEs. Approval does not substitute for the separate correctness assessment of these valid states.

## Required implementation evidence

- Direct validation tests for all four versions, exact widths, missing/extra records, field/count limits, nonfinite/overflow/underflow values, list-directed controls, unsupported quoting and comments at native no-skip boundaries.
- Real source publication/reuse and failed replacement tests proving unchanged accepted bytes/hash and accurate version metadata.
- Generated single/multiple-OFE records at 1, 2, 12 and 32 OFEs, preserving sentinel `avke` and all 9002 values without Rosetta; explicit modifiers affect generated copies only.
- Native `wepp_260803` execution and nonempty outputs for new versions, including valid commented input and both adjustment-flag states where relevant.
- Ordinary WSU parser/writer behavior, legacy 7778 uploads, non-upload project behavior and canonical error envelopes remain unchanged.
- Final review checks contract ancestor commit, actual changed surfaces, correctness/QA evidence and observable artifacts before package closeout.

## Verdict

**Pass for the amended contract checkpoint.** The owner may commit the checkpoint and proceed with the bounded implementation. Final security approval remains pending the implementation and evidence above. Residual risk is the existing native model's format-specific calculations; this contract neither certifies arbitrary scientific parameter choices nor changes native formulas.

Security reviewer: `/root/soil_format_contract_security`, 2026-09-26.
