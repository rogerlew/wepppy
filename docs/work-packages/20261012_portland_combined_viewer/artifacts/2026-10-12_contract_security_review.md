# PCV-01 independent contract security review

## Findings

No unresolved findings in the proposed canonical contract.

| ID | Severity | Evidence and consequence | Required disposition |
| --- | --- | --- | --- |
| PCV-CSEC-01 | Low, resolved | The initial `package.md` described scaffold-only authority and required the same bounded policy for every downstream fetch. The current operator authorization and canonical contract instead permit forest execution and preserve ordinary ownerless downstream reads. Leaving both descriptions risked an unauthorized general access restriction. | Author updated Overview and Success criteria. Reviewer readback confirms forest authority and preserved downstream ownerless access; closed before checkpoint. |

## Verdict and metadata

- **Contract gate:** pass; documentation finding resolved by author and independently rechecked.
- **Reviewer:** independent `contract_security` agent, dedicated security reviewer role; not the contract author.
- **Initial review:** 2026-10-12 16:30:27 UTC; follow-up readback 2026-10-12 16:31 UTC.
- **Starting implementation:** `dc6f3879e3372fa35062708b2c2f0caeb7eba18e`.
- **Reviewed amendment:** [combined viewer contract](../../../ui-docs/contracts/combined-watershed-viewer-contract.md), all sections; [feature access contract](../../../schemas/feature-access-governance-contract.md), PCV-01 amendment; [contract decision](2026-10-12_contract_decision.md), including its execution authorization and resolved matrix.
- **Security impact:** high because collection admission changes authenticated resource access and accepts arbitrary run lists.
- **Approval limit:** approval of the proposed pre-implementation boundary only. It does not approve implementation, production writes, deployment, or package closure. The independent correctness/UX gate and final dedicated security review remain required.

## Authority and scope

The operator authorized forest implementation through rollout readiness, forest stack restarts, and dev-agent account permission changes. That supports the proposed local work and its necessary checkpoint. It does not authorize changing production roles, publication markers, access policy, or run data during this execution.

The finite version-controlled association of the 63 inventoried IDs is a sufficiently bounded resource authority. Current authenticated `PortlandGroup` membership may admit those IDs only. A prefix, submitted configuration, feature entitlement, or unverified JWT group string cannot enlarge that set. Every selected run must pass its own grant; mixed lists fail as a whole. The existing role check at `wepppy/weppcloud/routes/locations.py:62` supports reusing the established account role without a membership migration.

Explicit PUBLIC, owner, and existing Admin/Root grants remain independent. The ownerless legacy rule does not become a collection-entry grant. Conversely, collection denial is not a new embargo on ordinary resource reads. These distinctions are explicit in the canonical contract and do not conflict with the feature-access contract's preservation of existing ordinary authorization.

## Evidence and compatibility

Parsed [production inventory](evidence/production-inventory.jsonl): 63 records, 63 unique run IDs, nine collections of seven runs, every run present, zero PUBLIC markers, zero owners, all retained loss text present, and no loss Parquet. This review inspected retained inventory; it did not independently connect to production.

Current source corroborates the reported policy mismatch: `wepppy/weppcloud/routes/combined_watershed_viewer.py` admits only `Ron.ispublic()`, while the ordinary authorization path in `wepppy/weppcloud/utils/helpers.py` admits ordinary runs with no owners. The proposed fix can therefore restore collection entry without altering general authorization or query-engine policy. Any actually private downstream resource that later fails must receive a new exact-surface checkpoint; this contract cannot be used to widen general `authorize()` or mutation access.

Absent/empty viewer and generator states remain reachable. Populated PUBLIC and independently owned collections retain their grants. Supported legacy ownerless Portland collections become available to current members. Missing optional phosphorus remains an explained unavailable choice. Missing required artifacts produce a bounded error for authorized callers. Malformed IDs, hostile settings, unrelated private runs, and mixed unauthorized collections fail explicitly. These state obligations satisfy the contract-level noninterference requirement; runtime proof is still pending.

## By-surface security assessment

| Surface | Contract assessment and required implementation evidence |
| --- | --- |
| Authentication and revocation | Current account membership is checked per collection request. Exercise member access and role removal with the same session, including a non-admin member, plus independent PUBLIC/owner/admin grants. |
| Authorization and disclosure | Catalog membership is exact and server owned; authorize all runs before releasing metadata/readiness details. Unauthorized lists return generic 403 without naming denied runs. Preserve ordinary ownerless downstream access in direct endpoint checks. |
| Inputs and rendering | Bound collections to 100; reject malformed identifiers, JSON, nonfinite/out-of-range settings and unknown enums. Submitted config is not authority. Test path traversal and encoded variants at the real resolver, and titles/IDs containing markup at the actual template/DOM boundary. |
| Session, CSRF, and credentials | Generator POST retains the canonical CSRF policy; generator does not assign roles. Existing query/browse token transport remains unchanged. No credentials belong in share URLs, screenshots, or retained browser artifacts. |
| Files and data integrity | Offline additive preparation preserves originals and PUBLIC/READONLY markers, refuses unexpected existing outputs, and records source/writer/output provenance. Test an actual writer, failure retention, and package-owned rollback under the forest runtime identity. No conversion runs on page GET. |
| Queue and subprocess | No queue, model execution, new daemon, or model rerun is authorized. Review any preparation command composition in the final implementation review. |
| Egress, dependencies, and deployment | Existing Deck.gl/query components are reused; no new service or dependency is authorized. Production rollout remains a later operator action. |
| Observability | Required missing data cannot yield a successful partial/empty map. Provenance, failure evidence and generated outputs remain inspectable through established authorized tooling and archive/restore coverage. |

## Residual risk and required closing evidence

Existing ownerless data visibility is intentionally preserved, not newly granted by Portland membership and not claimed private by this review. Revoking membership removes only group-derived collection admission; independently valid downstream access remains possible. This is the contract's explicit compatibility disposition, not an unresolved security finding.

The later READONLY maintenance paragraph is approved within the same boundary: explicit operator-invoked preparation on forest may use a visible staging copy and publish only validated manifest-owned derived files and an existing-builder catalog, while preserving original bytes and the READONLY marker. This is not permission to disable ordinary runtime read-only guards, mutate source NoDb, overwrite unowned outputs, or operate on production. Final writer tests must prove staging cannot modify original paths, rejection of unowned existing output/catalog, partial-failure visibility, and rollback ownership.

Final review must examine the implementation diff, two-review checkpoint ancestry, direct valid/hostile authorization and filesystem tests, real browser member/nonmember/revoked-member evidence, CSRF and rendering safety, catalog equality with this inventory, and unchanged original artifacts. Tests that mock the changed authorization or filesystem boundary cannot alone close those checks. Security approval cannot replace scientific-value correctness or user-experience acceptance.

## Validation

- Read-only source and contract inspection; no runtime files, roles, services, or production resources changed.
- Inventory parsed with Python JSON and collection/identity counts checked.
- `wctl doc-lint --path docs/work-packages/20261012_portland_combined_viewer/artifacts/2026-10-12_contract_security_review.md`: pass, zero errors/warnings.
- `diff -u <review> <(uk2us <review>)`: no spelling changes.
