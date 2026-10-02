# FA-02 correctness and user-experience contract review

## Metadata

- Reviewer: `/root/contract_correctness`, independent review, 2026-10-02 UTC.
- Base: M3 checkpoint `458557219`; reviewed documentation amendments in the working tree.
- Scope: FA-02 checkpoint, canonical feature-access contract, governance policy, ADR-0001/0080, registry specification, browse/RQ/query contracts, developer guide, package, active ExecPlan and tracker.
- Authority: [FA-02 checkpoint](2026-10-02_fa02_sharing_checkpoint.md) and [feature-access contract](../../../schemas/feature-access-governance-contract.md), particularly Public project visibility, Authorization composition and Protected-data classification and mixed delivery.
- Related evidence: [historical M3 security review](2026-10-02_m3_security_review.md). Earlier FA-01 matrices/reviews remain evidence of their assessed policy.
- Write scope: this artifact only; no implementation, account, credential or deployment changes.

## Findings and disposition

| ID | Severity | Evidence and consequence | Required correction / disposition |
| --- | --- | --- | --- |
| FA02-C01 | Medium | Registry specification, Runtime Availability Rules, lines 160–163 retained a feature-entitlement requirement for embargoed reads, contradicting FA-02 and its own updated enforcement rules | Closed on source readback: retained results now use normal resource access; private workflow scope remains separate |
| FA02-C02 | Medium | Active ExecPlan M1, line 137, and governance policy Internal Collaborator Onboarding, line 687, retained the requirement for separate contrast entitlement merely to consume retained inputs | Closed on source readback: plan and policy distinguish actual composed contrast execution from retained input reads; developer guide identifies superseded current UI guidance for reconciliation |
| FA02-C03 | Low | Canonical UI and backend obligations, line 154, retained a prohibition on regenerating protected artifacts, conflicting with permitted report formatting/packaging in Authorization composition and mixed delivery | Closed on source readback: prohibition now covers optional controller initialization and restricted scientific analysis, consistent with retained-output rendering/packaging |

Line references identify the reviewed snapshot and may move. These are documentation defects, not demands for runtime acceptance before the contract checkpoint.

## User outcome and valid states

The intended outcome is clear: an authorized feature user may share retained results through ordinary project/resource sharing. A recipient gains no permission to activate, configure, acquire data for, execute, retry, cancel or delete the restricted feature. Private grouped reads retain their separate live workflow entitlement. Account groups, audit history, acknowledgment and technical-role exceptions are unchanged.

| State | Valid? | Required outcome and contract evidence |
| --- | --- | --- |
| Public project; optional feature absent or never used | Yes | Explain that results are unavailable without initializing the restricted controller, acquisition or analysis; checkpoint regression plan |
| Public empty/populated feature state | Yes | Existing readable state and results remain visible; disabled actions explain missing permission |
| Retained contrasts used as PATH-CE inputs | Yes | PATH-CE action permission applies; input reads alone need no contrast action grant; canonical Authorization composition |
| Composed operation actually executes contrasts | Yes, with corresponding permission | Contrast action entitlement also applies; no implicit membership or dependency activation |
| Public retained results after group removal or expiration | Yes | Results stay shareable; future restricted actions are denied before writes/enqueues |
| Public readonly project or unsupported current backend | Yes | Retained results remain readable; readonly/backend constraints still apply to relevant actions |
| Private ordinary project / private Batch or Culvert root | Yes | Existing private-resource and separate grouped-read admission remain; result sharing does not make the source public |
| Public Batch / registered Culvert integration | Yes | Preserve the public Batch exception and independent, scoped service path; no anonymous Culvert root or renewed expired credential |
| Supported legacy aliases, copied results, archive/restore | Yes | No inherited feature-result embargo or ancestry-only denial; actual restricted operations remain gated |
| Malformed state, hostile paths, revoked/expired credentials | No or exceptional | Preserve existing explicit errors, sensitive-file rules, containment and credential validation |

This matrix is bounded contract coverage. It does not claim that runtime tests have exercised these states.

## Error policy and compatibility

- Missing optional results are an expected readable state, not permission to run the feature or an internal error.
- Denied restricted actions must fail before state writes, external calls, timestamps or queue submission. Already-admitted work may finish under the unchanged admission-timing contract.
- Required membership/configuration failures remain explicit unavailable responses. Public shared-result reads acquire no unnecessary feature-account lookup dependency.
- Existing endpoint authentication, token classes, scopes, session/run binding, CSRF, private resources and sensitive files remain independent requirements. No universal D-Tale login, new sharing credential, scope/TTL change or DuckDB upgrade is authorized.
- Formatting retained output differs from scientific execution. Current PATH-CE worker documentation already identifies preexisting contrast inputs rather than automatic Omni provisioning; FA-02 changes admission, not scientific formulas or parameterization.

The checkpoint correctly treats the old SQL-expression and cached D-Tale findings as requiring reassessment against actual private-resource/containment boundaries. It neither declares those defects technically fixed nor treats intended public result sharing as an exploit. Historical negative result-read tests must be replaced with positive sharing cases and retained negative action/private-resource cases.

## Evidence and observability limits

| Evidence stage | Result |
| --- | --- |
| Approved intent and canonical contract consistency | Reviewed in documentation; all three findings independently confirmed closed |
| Persisted account/project state, generated intermediates, executable input and fresh outputs | N/A to this documentation-only checkpoint; no producer or stored state was changed |
| Browser, download/ZIP bytes, query, fork/restore and service behavior | Explicit later M3 acceptance; no runtime pass asserted by this review |
| Artifact observability | Contract preserves ordinary catalogs, reports, raw/shared data, downloads and archive/restore; introduces no hidden lineage marker or artifact schema |
| Deployment/recovery | M3 remains incomplete and undeployed; production acceptance and Culvert credential renewal remain separate authorized work |

Source/diff inspection found documentation changes only in the reviewed delta. The contract regression plan covers anonymous readers where already permitted, nonmembers, removed members, current members, individual technical roles, private roots and service credentials. Runtime proof remains necessary before implementation closeout, but is not a prerequisite to reviewing this preparation checkpoint. Scoped documentation lint, spelling preview and whitespace checks passed for this artifact.

## Verdict

- Gate status: **pass for the documentation/contract checkpoint**.
- Unresolved findings: High **0**; Medium **0**; Low **0**.
- Release recommendation: **ship the documentation checkpoint** after the independent security review and author disposition are recorded. M3 reconciliation, executable regression, privacy/containment findings and browser/service acceptance remain outstanding; no runtime or deployment approval is implied.
- Reviewer: `/root/contract_correctness`, 2026-10-02 UTC.
