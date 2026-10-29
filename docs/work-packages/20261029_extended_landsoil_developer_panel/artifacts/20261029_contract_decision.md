# DM-02 contract checkpoint

Date: 2026-10-29 UTC. Starting revision: `981caadf553c12b1199b9d76f5a28c100b6722e3`.
Status: independently reviewed; all findings dispositioned and closure confirmed; no implementation ancestor commit yet.

## Authority matrix

| Contract | Application / delta |
| --- | --- |
| DM-01, DM-02 in `docs/schemas/project-developer-mode-contract.md` | Add full/simple panel predicate and reload semantics; preserve Ron activation/lifecycle |
| `docs/ui-docs/controller-contract.md` | Existing selectors, delegated actions, feedback and missing-DOM behavior; no shared contract change |
| `docs/schemas/weppcloud-csrf-contract.md` | Existing protection retained; no delta |
| `docs/schemas/nodb-persistence-concurrency-contract.md` | No new state/mutation path; read existing getter |
| `wepppy/weppcloud/feature_registry/specification.md` | Presentation-only project capability outside entitlement registry; no registry entry |

Operator approval: current conversation requests full panel for developer projects or currently Extended, simple panel with Reset Base and Modify Base otherwise, preservation of configured extended projects, and no backend enforcement. The operator then explicitly accepts loss of full access after selecting Base/deleting Extended and will arrange Dev roles. Scope now is assessment/scaffold, not execution.

Classification: intended UI behavior change; existing full panel for all enabled projects is current behavior, not a defect against the new requirement. Normative delta and rationale are in DM-02. Compatibility is based on `active_lookup_variant`, including legacy file fallback; no migration, table destruction or sticky grant. Current base selection plus an unused extended file intentionally remains simple.

Security: low; no authorization boundary changes. Existing direct editor/API calls remain authorized under their current contracts. Hiding controls is not represented as a security mechanism. Existing malformed-state errors, readonly, module eligibility and CSRF remain effective.

Regression evidence required: real getter/state matrix, actual rendered actions, sparse DOM controller lifecycle, base reset/edit CSV readback, unchanged legacy Extended workflow, same-page/reload behavior, and no backend developer gate. No generated-parameter or native policy change is authorized. No new parameterization ADR is needed.

Before runtime edits: obtain two independent read-only reviews, disposition findings, obtain execution/commit authority, and commit the reviewed contracts/package alone as the implementation ancestor. Retain exact SHA and timestamps. Do not amend the closed DM-01 execution package.

Review correction: report shells also include the modal but commonly omit Disturbed context. The implementation may add a bounded shared presentation-state read through existing NoDb APIs for the active root; this must not create missing state or change backend operations. Report-shell real-state coverage and frontend gates are mandatory.
