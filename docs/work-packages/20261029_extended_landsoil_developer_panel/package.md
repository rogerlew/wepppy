# Extended landsoil developer-project panel

Status: Closed — implemented and locally validated, 2026-10-29 UTC. Production deployment remains separate.

## Scope and authority

Implement the [DM-02 presentation amendment](../../schemas/project-developer-mode-contract.md#extended-landsoil-panel-presentation-dm-02): full Disturbed Panel for developer projects or the resolved Extended selection; otherwise only Reset Base and Modify Base lookup actions. Preserve all backend operations and active extended projects. The operator explicitly accepts that selecting Base/deleting Extended on a normal project loses full-panel access after reload and will arrange Dev roles for those users.

The operator has now authorized execution of the [plan](prompts/completed/implementation_execplan.md), including the reviewed contract ancestor commit and isolated validation. Production deployment and role assignment remain outside scope. Starting revision: `981caadf553c12b1199b9d76f5a28c100b6722e3`.

## Assessment and complexity budget

The plan fits current mechanisms. `Disturbed.active_lookup_variant` already handles explicit selection and legacy extended files. `disturbed_modal.htm` contains all actions; the run header already exposes the Disturbed launcher for enabled modules. `disturbed.js` uses query-selector arrays and refreshes metadata, so absent advanced controls should require only regression coverage, not a new controller mode. The base editor link must remain `lookup=base` and reset feedback must still work.

Both the run page and `reports/_base_report.htm` include this modal. Report routes may omit a Disturbed template variable; add only the bounded shared presentation-state read needed to resolve the active page/run root, without constructing missing state. Missing context is not equivalent to absent `disturbed.nodb`.

Prefer conditional groups in the existing template, shared base actions and existing help/status markup. Do not duplicate the full modal, add persistence/grandfather flags, change controller or native parameter policy, introduce a feature-registry entry, or gate backend calls. Layout changes on page render only; document reload after developer activation. Backend enforcement was explicitly rejected. There is no dependency, service or queue change.

## Compatibility and state matrix

| Ron mode | Resolved lookup/state | Expected presentation |
| --- | --- | --- |
| Missing/false | Base; no extended file | Simple |
| Missing/false | Explicit Base; extended file exists | Simple; preserve file |
| Missing/false | Explicit Extended; populated or empty file | Full; existing validation still applies |
| Missing/false | Legacy selector absent/invalid; extended file exists | Full via existing getter |
| Missing/false | Explicit Extended; file missing | Full; preserve existing recovery controls |
| True | Base, Extended, or no extended file | Full |
| Any | Disturbed module disabled/absent | No Disturbed panel; no new state creation |
| Malformed Ron mode | Any | Existing explicit error, no permissive fallback |

Role and state are independent: a non-Dev user sees full controls on an eligible project; a Dev user sees simple controls on a normal Base project. Existing auth/readonly/CSRF behavior remains. Normal Extended-to-Base/delete transitions become simple on reload; same-page layout remains stable. Cloning/restoring incoming state recomputes the same predicate. No data/schema mutation or parameterization ADR is required: no values, formulas, thresholds, defaults or fallback algorithms change.

## Validation and artifact gate

Generated-artifact gate: applicable, bounded. Record actual rendered normal/developer/legacy panels, working base editor/reset requests and CSV readback on disposable projects. Compare saved selector, existing extended CSV and prepared outputs before/after a read-only render and developer activation; rendering/activation must not alter them. A fresh model run/native rebuild is unnecessary unless implementation expands into parameter generation, which requires reassessment. Validate legacy Extended editing and normal direct API use still work. Preserve source projects and retain exact runtime/revision evidence.

Run focused template, Disturbed controller and route tests; frontend lint/tests for template changes too; rebuild the bundle only if controller source changes; full Python sanity for the runtime implementation per root guidance. Add no tests merely asserting documentation or literal config text. Exercise explicit Extended, legacy Extended and explicit Base in both run and report shells, including reports with no supplied Disturbed template context. Use real getter/file boundaries for legacy/missing-file states and HTTP/browser readback for discoverability, not mocks alone.

## Reviews and success criteria

Security impact: low. This intentionally changes discovery without changing any authorization boundary. Two independent contract reviews are required by the contract-first standard; retain correctness and security/noninterference findings. Dedicated implementation security review is required if scope expands into authorization/persistence, otherwise a scoped noninterference review is sufficient.

- [x] Inspect source and record compatibility assessment.
- [x] Amend DM-02 and Usersum guide, clearly marking rollout pending.
- [x] Independent contract reviews and disposition complete; all three correctness findings closed, security reconfirmed.
- [x] Reviewed contract ancestor `2fb0a4dd2` committed before runtime implementation.
- [x] Template/controller regression matrix and real CSV/browser evidence pass.
- [x] Implementation review, docs, tracker and final gates complete.

Owner: requesting operator. Implementation and local runtime/browser acceptance complete; full Python gate passed (12,072 passed, 298 skipped). Only disposable validation projects were mutated; source projects and real account roles are unchanged. Production rollout remains separate.

Review evidence: [correctness](artifacts/20261029_contract_correctness_review.md), [security/noninterference](artifacts/20261029_contract_security_review.md), and [disposition](artifacts/20261029_review_disposition.md). No operator decision remains open.

Completion evidence: [validation](artifacts/validation.md), [implementation correctness](artifacts/implementation_correctness_review.md), and [implementation security](artifacts/implementation_security_review.md). Both reviews passed without findings.
