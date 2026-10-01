# FA-01 contract decision checkpoint

Prepared: 2026-10-01 20:47 UTC

Starting implementation revision: `45a39a8337d37c7f7d30087ff4d23c03610072b3`

Status: Reviewed amendment committed in `4cd85e2d5` and review dispositions in `36f35b6f0`; milestone-zero investigation and independent design reviews complete; accepted ancestor recorded in tracker; runtime conformance untested.

## Authority and exact direction

The user requested the assessment, then directed public-project read-only feature views, internal Batch/Culvert workflows, conservative maturity and single-maintainer auditable group changes. The user explicitly required separate group enforcement with only their account initially admitted for OpenET/Batch, deferred PowerUser suspension/reapplication/permanent revocation, and requested the reconciled amendment and implementation plan.

The subsequent M0 direction supplied rogerlew@gmail.com on every deployment and the wepp2 Culvert client location, and explicitly preserved all ordinary anonymous functionality. Read-only investigation resolved account IDs and credential metadata. No global writer gate, creator credential, embargo release, rotation or deployment is authorized. Preserve the current embargo exception and credential behavior while resolving the technical inventory. The operator subsequently authorized committing this prepared amendment, producing `4cd85e2d5`, and then requested independent review and findings disposition. That commit is preparation evidence, not an accepted runtime checkpoint.

## Canonical authority matrix

| Contract | FA-01 delta or preserved invariant |
| --- | --- |
| `docs/schemas/feature-access-governance-contract.md` | New bounded owner for inspect/action separation, group-only and role-or-group decisions, records, admission timing and exclusions |
| `wepppy/weppcloud/routes/usersum/weppcloud/feature-maturity-and-release-governance.md` | Single-maintainer groups replace dual-reviewer workflow; public reads separate from actions; conservative maturity; sanctions deferred |
| `wepppy/weppcloud/feature_registry/specification.md` | `access_group`/`access_mode`, independent public inspection, finite conservative multi-OFE override |
| `docs/adrs/ADR-0080-feature-access-governance-amendment.md` | Authority, rationale, compatibility and reserved decisions |
| `docs/adrs/ADR-0001-time-limited-publication-embargo-for-omni-contrasts.md` | Add scoped group entitlement alongside Dev/Root; preserve embargo dates and public-data exception; PATH-CE dependency remains |
| `docs/schemas/weppcloud-browse-auth-contract.md` | Human private grouped access uses current workflow group rather than broad role claims; existing public Batch and scoped service reads preserved |
| `docs/dev-notes/auth-token.spec.md` | Groups are not durable JWT authority; preserve credential validation and existing Culvert integration/browse token distinction |
| `docs/schemas/rq-engine-agent-api-contract.md` | Internal admission checks compose with scopes/run identity; no new service-role requirement or polling-mode change |
| `docs/schemas/project-creation-policy.md` | Informational visibility is not launch permission; preserve current named presets/anonymous defaults; no internal presets introduced |
| `docs/schemas/weppcloud-csrf-contract.md` | Existing origin and CSRF boundaries unchanged; new browser endpoints must conform |
| `docs/schemas/weppcloud-session-contract.md` | Both session issuers preserve trusted human provenance for restricted admission; ordinary anonymous sessions unchanged |
| `docs/schemas/rq-response-contract.md` | Conditional protected result projection across single/batch/recursive polling; lifecycle, queue and ordinary Culvert polling unchanged |
| `wepppy/query_engine/README.md` | Canonical web/MCP query owner: protected catalog/query/result projection and trusted human provenance; ordinary anonymous query/cache behavior unchanged |
| `docs/schemas/nodb-persistence-concurrency-contract.md` and artifact standards | Read-only views do not initialize/mutate state; actual execution/output evidence required |
| Current feature/controller domain contracts named during surface freeze | Must be registered and reconciled before touching their covered behavior; package is not authority to bypass them |

## Discrepancy classification

Intended changes: additive groups/account records, human group-only OpenET/Batch/Culvert admission, PowerUser self-service, public inspect/action separation and conservative override behavior. These require the full pre-implementation checkpoint, not a conformance-fix shortcut.

Existing discrepancies include OpenET's Dev-visible/Admin-execute split, broad private grouped user-token admission, PATH-CE/AgFields missing feature checks, and the universal MOFE Preview override. The new policy determines their intended correction. The generic public-writer proposal is withdrawn; only feature-specific actions, protected workflow aliases and retained embargo boundaries change.

## Compatibility and schema plan

Use additive account tables/constraints; preserve User IDs, role/run relationships and historical events. No run CSV/parquet/NoDb schema changes or model parameter edits are planned. Explicitly initialize only the approved group memberships after canonical identity verification. Do not backfill fabricated training, transform every Dev/Admin into a collaborator, or infer service grants from human groups.

Keep non-targeted technical-role powers, existing named-preset creation and currently authorized Culvert service behavior. Group-only features intentionally stop admitting a human on broad role alone. Current public Batch reads remain; no anonymous Culvert root is added. Existing jobs can finish, with subsequent reads checked normally. Rollback retains audit data and closes new admissions rather than restoring a role bypass.

## Security and regression plan

Security impact is high. Test real persistence transactions and every changed auth boundary with both valid and hostile states. Freeze the surface inventory for public reads, private reads, actions, mixed bundles and service credentials. Include current-role matrix, group membership removal with a stale JWT, Root without group, scoped user without technical role, private resource mismatch, public empty feature state, legacy account, readonly project, backend/prerequisite mismatch and valid service tokens.

The 275 prior tests are assessment evidence only. Runtime acceptance requires focused and broad tests, accessible browser flows and real authorized model/output readback. Two independent pre-implementation contract reviews, plus independent correctness/security implementation reviews, are required by repository standards. The prepared amendment has now received independent contract reviews; see [findings and disposition](2026-10-01_contract_reviews.md). These do not substitute for review of the completed milestone-zero matrix or implementation evidence.

The operator subsequently requested “commit and then execute milestone 0.” Commit `36f35b6f0` fulfills the first step. [Source and deployment evidence](2026-10-01_milestone_zero.md) and the [credential matrix](2026-10-01_credential_matrix.md) record execution of the second; no runtime authority is inferred.

## Remaining checkpoint steps

The account/credential and source matrices are in [M0 evidence](2026-10-01_milestone_zero.md). The operator's scope clarification supersedes earlier broad writer/creator recommendations. Final independent reviews accepted the narrowed canonical matrix after fixes; see [M0 disposition](2026-10-01_m0_reviews.md). Commit the standalone ancestor. Record its SHA in the tracker before runtime work.

The configured Culvert credential is expired; normal production verification rejects it. Renewal and positive live integration acceptance remain separately authorized implementation/rollout dependencies. No runtime edits, scope expansion, expiry bypass or credential mutation is included in this checkpoint.
