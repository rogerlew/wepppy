# Correctness and User-Experience Review - Modify Landuse MOFE

## Metadata

- **Package**: `docs/work-packages/20260911_modify_landuse_mofe/`
- **Reviewer**: Independent read-only review by `/root/contract_review_1` (implementation review; sign-off pending boundary evidence)
- **Date**: 2026-09-11
- **Scope reviewed**: `Landuse.modify`, MOFE synthesis override path, selected-landuse route behavior, and focused tests
- **Commit/branch context**: implementation working tree after contract ancestor `134a3a9af`
- **Canonical contract(s)**: `docs/schemas/landuse-modification-contract.md`
- **Related QA/security artifacts**: `docs/work-packages/20260911_modify_landuse_mofe/artifacts/20260911_contract_decision.md`

## User Outcome

- **User goal**: Apply a landuse class to selected hillslopes in a multi-OFE project.
- **Success presented to the user as**: Existing route response, with regenerated `hill_*.mofe.man` files and a reloaded summary containing the class and OFE-derived area.
- **Failures that may reach the user**: Validation errors for unknown classes, missing/incomplete MOFE state, and existing route errors for synthesis or persistence failures.
- **Partial-state behavior**: Existing landuse logs, status panel, and error envelope expose failure; files are not treated as complete until a successful retry.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Single-OFE state | yes | Existing assignment and summary rebuild | Existing route tests; focused code path |
| MOFE state absent/never built | no for multi-OFE | Explicit build-first error before mutation | `test_modify_rejects_unbuilt_mofe_state` |
| MOFE state populated and complete | yes | Update selected OFEs, synthesize files, rebuild summary | `test_modify_regenerates_mofe_assignments_and_managements`; synthesis override tests |
| Supported legacy nested assignment state | yes | Preserve nesting and use existing builder normalization | Contract; builder override tests |
| Empty, incomplete, or malformed MOFE state | no | Explicit error before mutation | `test_modify_rejects_incomplete_mofe_state` |
| Unknown class or selected ID | no | Validation error; no assignment mutation | `test_modify_rejects_unknown_class_before_mutation`; existing route validation tests |
| Optional Disturbed/SBS absent or unusable | yes for explicit assignments | Explicit override bypasses burn lookup | `test_explicit_mofe_assignments_do_not_require_disturbed_burn_lookup` |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Unknown class/selection | expected | Existing validation error envelope | Landuse modification contract |
| Missing or malformed required MOFE state | expected project-state failure | Existing validation error path; no mutation | Landuse modification contract |
| MOFE writer failure | exceptional | Existing route error, log/status evidence, retry required | Artifact observability and contract |

## Review Checks

- [x] Canonical intent is named.
- [x] Required state dimensions are enumerated separately from request inputs.
- [x] Explicit assignments bypass optional burn lookup.
- [x] Focused regression tests cover validation and synthesis wiring.
- [ ] Direct unmocked persistence, archive/restore, browser/download, and downstream WEPP preparation evidence remains to be run before approval.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | High | Artifact and downstream boundaries | Focused tests use test doubles for NoDb locking and management synthesis; they do not establish live archive/browser/downstream evidence. | Focused pytest results | Run production-equivalent disposable-run checks before approval. | Open |

## Verdict

- **Gate status**: `fail pending boundary evidence`
- **Unresolved findings**: High 1; Medium 0; Low 0
- **Release recommendation**: `hold`
- **Reviewer sign-off**: pending direct boundary evidence

## Artifact Observability Gate (Required)

- [x] Existing landuse layout, parquet summary, logs, and status/error paths are named.
- [ ] Real writer/failure, archive/restore, browser/download, and downstream preparation evidence remains required before production rollout.
