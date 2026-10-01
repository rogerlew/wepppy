# FA-01 milestone-zero checkpoint evidence

Starting source revision: `36f35b6f0`. Runtime files are unchanged. The operator authorized milestone zero, not later implementation or deployment. Status: independent correctness/security reviews passed after fixes; accepted ancestor is recorded in the package tracker.

## Operator clarification and scope correction

The operator identified `rogerlew@gmail.com` on every deployment and `/workdir/Culvert_web_app` on wepp2. The operator then clarified: only limited-access features become read-only for users without their entitlement; anonymous creation and functionality remain unaffected.

This supersedes the earlier proposed global public-writer boundary. No creator credential, login requirement, legacy ownerless-run migration, recovery mechanism or change to ordinary collaborator/public-editing semantics is included. The source observations about absent anonymous creator proof remain true but are not defects to fix in FA-01. Engineering review must preserve this explicit product boundary.

## Verified account and integration evidence

Read-only checks, 2026-10-01; host identities verified before inspection. The operator skill was `/home/roger/.codex/skills/wepp1-operator/SKILL.md`. No database, group, credential, job or deployment mutation occurred. Only allowlisted credential metadata was emitted; bearer values and signing secrets were never printed or retained in artifacts.

| Evidence | Result |
| --- | --- |
| Local account database | Exact email match, active User ID 1; Admin/Dev/PowerUser/Root/User |
| wepp1 production account database | Exact email match, active User ID 12; Admin/PortlandGroup/PowerUser/Root/User |
| Initial memberships | Resolve the email on each deployment; seed only this account in separate OpenET/Batch groups with an audit event. Do not copy numeric IDs between environments or authorize by email |
| Culvert deployment | `wepp2`, `/workdir/Culvert_web_app`, revision `c0b5fde5bf10261d4001851032c4a0f12c3d7527`; Compose web/worker/Redis running |
| Local Culvert checkout | Revision `8be2edc2dac884dded77a6a7fe03ffd346170c97`; the two relevant client source files match deployed worker/source SHA-256 exactly |
| Client environment source | Worker `/app/.env` loaded with dotenv plus existing environment; target `wepp.cloud` |
| Operation credential metadata | HS256; subject `culvert-batch-submit-90d`; audience `rq-engine`; service class; `service_groups=culverts`; `culvert:batch:submit` only; `jti` present; no run claims |
| Credential fingerprint | SHA-256 `df4adf2fb2b2ebdda2b8066c3b05858d32490c3b1041cf9134dc1c367be7bd05` (reference, not runtime identity or a bearer value) |
| Validity | Issued 2026-06-03 20:38:14 UTC; expired 2026-09-01 20:38:14 UTC |
| Actual verifier check | wepp1 `docker-rq-engine-1`: signature matches configured validation keys; normal `decode_token(..., audience='rq-engine')` rejects as expired |
| Polling | wepp1 rq-engine configured mode `open`; no need for `rq:status` to use this existing open path |
| Server deployment revision | wepp1 `/workdir/wepppy` at `50495bfeebf5ccf3c8cf50753100803e35bb5382` |

The attempted check in wepp2's WEPP worker found no JWT verifier configuration; it did not establish validity. Verification was therefore performed in the actual wepp1 rq-engine container. The token traveled only through process pipes/SSH and was not persisted. No fresh token was minted and no expired-token acceptance was introduced.

Client source evidence: `tasks/submit_payload.py` SHA-256 `e1c6349888b436e0602d13c07a96250563b6d42994d67e6a74ed1c47916200dc`; `tasks/wepp_cloud_integration_task.py` SHA-256 `673ff9b03fc304662dee6d489d624b7bbfdad7971fc5511443835882cfe5d061`. The deployed client submits a payload, polls/reattaches using the operation credential, and downloads `weppcloud_run_skeletons.zip` using the returned browse token. It does not call retry/finalize/cancel in these integration paths. Local cancellation callbacks are not remote Culvert cancellation requests.

**Operational limitation:** the configured token is expired. Design/source reconciliation can proceed with that known fact; successful live integration acceptance and rollout require separately authorized credential renewal and a positive workflow. This is not a permission to rotate credentials, bypass time validation or change polling mode. The [credential matrix](2026-10-01_credential_matrix.md) records exact server operation requirements.

## Exact route surface and admission rules

[Route inventory](2026-10-01_route_inventory.tsv) records 516 declarations from 79 source files, including all explicit rq-engine and Flask NoDb API declarations plus profile/admin, run page, Batch, browse/download/report, query/MCP and fork/archive surfaces. Each row retains source path/line, declared method/path, handler, decorators and the bounded FA-01 rule. Ten additional parsed modules contain no declarations. This is a source registration snapshot, not a claim that every legacy endpoint changes.

Flask paths are relative to the stripped `/weppcloud` prefix; rq-engine routers use `/api` under `/rq-engine`, except the explicitly mounted creation route/compatibility alias. Query-engine is mounted at `/query-engine`, with MCP under `/mcp`. `prefix_path(...)` records the exact source expression. Framework HEAD/OPTIONS behavior remains. `docker/caddy/Caddyfile` routes PATH-CE reports to browse, archive ZIPs to dedicated download, and published feature/ERMiT launchers to Flask; tests must exercise those distinct consumers. No proxy configuration change is planned.

| Exact handler family (paths in TSV) | Frozen FA-01 obligation |
| --- | --- |
| `acquire_openet_ts`; OpenET mod enable/config actions | `openet_ts` current group, acknowledgment for group-based action, existing run/scope/capability checks; public retained output view without acquisition |
| `run_omni_contrasts`, dry-run, delete; contrast report | `omni_contrasts` group or preserved Dev/Root, action or embargoed-read decision; entitlement checked before existing report generation/reads; unentitled callers cannot generate or inspect embargoed data |
| PATH-CE enable, config POST, run | `path_ce` group or preserved Dev/Root, plus contrast entitlement when consuming contrast data; existing optional-controller GET must not create restricted state for an inspect-only caller |
| PATH-CE status/results/report | Read retained state; derived contrast outputs require contrast read entitlement |
| AgFields upload/schema/build/run/clear/save/delete | `ag_fields` group or preserved Dev/Root; ordinary run checks remain; GET views retain non-embargoed public inspection; `_state_snapshot` can persist interrupted-job reconciliation, so inspect-only state must use an observational projection |
| Batch create POST/directives/validation/uploads/run/delete | `batch_runner` current group; one initial member; private human workflow reads require it; public-base read exception retained |
| Culvert submit/retry/finalize | Registered independent service under its existing operation scopes, or group-authorized human with independently supplied existing scopes; no automatic service delegation |
| `task_set_mod`, `view_mod_section`, run page | Feature-specific decision only; ordinary modules and anonymous behavior unchanged; no inference that an enabled restricted mod locks the project |
| Shared rq/Flask mutation on Batch/Culvert/contrast-child aliases | Apply workflow/contrast check by canonical resolved resource, not only by launcher URL. Includes bootstrap, generic model/build operations and cancellation. Ordinary run IDs retain existing behavior |
| `jobstatus`, `jobinfo`, `jobinfo_batch` | Preserve polling mode and lifecycle/progress/queue fields; project protected contrast/PATH-CE results from single/batch/recursive nodes for unentitled callers, including auxiliary leaks; ordinary Culvert polling unchanged |
| `canceljob` | Resolve target job's protected workflow/feature admission; preserve independent Culvert submit-scope cancellation path. Ordinary cancellation and polling mode unchanged |
| Both session issuers; profile/admin-run/MCP issuance; grouped consumers | Restricted-operation provenance adapter, live human membership, existing resource/revocation checks. No general anonymous token invalidation or changed scope bundle/TTL |
| Generic file/schema/query/report/download, archive HEAD/range, forks/exports/restores | Additional restriction only for protected workflow resources or embargoed data identified below; ordinary unrelated functionality unchanged |
| Ordinary Omni scenarios/run/migration, project/collaborator controls, ordinary creation/fork/archive/export | Preserve existing authorization. Incidental invalidation of PATH-CE timestamps/preflight during ordinary work is not restricted-feature execution |
| Project config availability/preview/apply | Preserve section 13 of project-owned-config contract: current authenticated owner/Admin/Root/direct-user-token checks and worker recheck; no widening or tightening |

For mixed-method handlers, inspect and action are separate decisions. PATH-CE's current GET enable is an action, so the covered feature operation must move to a CSRF-protected mutation transport while its GET becomes non-mutating; do not reclassify ordinary unrelated GETs in this package. An authorized group's operational access remains subject to the existing project `readonly`, backend, prerequisites and token boundaries. Do not add a global `require_owner` requirement to `authorize()`.

## Protected data and mixed delivery

The canonical FA-01 contract's protected-data section owns the finite initial classification: contrast aggregate/documentation/selection/overlay products, contrast child trees and aliases, contrast fields of `omni.nodb`, result fields in `path_ce.nodb`, mixed status/config/dashboard payloads, and PATH-CE contrast-derived data/report trees. GL dashboard `_get_omni_contrasts` is an additional catalog reader; omit only its protected entries for callers lacking entitlement. Sources are `omni_artifact_export_service.py`, `omni_documentation.py`, `omni_state_contrast_mixin.py`, contrast build/clone services and `path_cost_effective.py`.

Archive source currently excludes archives/transaction files, not contrast outputs (`project_rq_archive.py`). Fork rsync can retain summaries even if a child tree is skipped (`project_rq_fork.py`). Therefore apply retained classification to supported copies and destinations; do not treat a filename-only exclusion or renamed transport as release authority. This is a boundary for system-supported data delivery, not a mechanism to prevent an already-authorized recipient from redistributing downloaded data.

Frozen response rule: omit unauthorized protected listing/catalog entries; deny direct protected files/datasets; project mixed structured responses explicitly; deny an indivisible protected bundle with a clear error rather than silently returning a partial archive. Non-protected data remains available. Query authorization checks referenced datasets before execution. Existing ordinary catalog/cache activation remains unchanged; a new inspect-only restricted-feature view must not generate that feature's missing state/results. No generalized taint service or run-data schema is introduced.

## Identity adapters and transport

Canonical `feature_access_principal` provenance and legacy handling are in FA-01's Tokens section. It is a trusted identity hint for restricted admission, never an entitlement. Scope includes verified Flask/user identity, both session issuers, trusted admin-run-token and command-bar MCP delegation, registered independent Culvert service, and returned browse derivatives. No arbitrary numeric service/MCP subject becomes a human account. Old sessions can continue ordinary functions; restricted access needs authoritative live human binding or authenticated refresh.

The canonical web transport section freezes Profile onboarding/acknowledgment and Root group-management methods, strict JSON bodies, CSRF, synchronous response fields, idempotency and error codes. No new endpoint is implemented by this checkpoint. Human Culvert operation tokens remain explicitly operator-issued with existing scopes; general PowerUser/profile bundles do not acquire Culvert scopes.

## Valid-state and regression matrix

Cross absent/empty/populated/working/failed/completed/restored/legacy/malformed feature state with anonymous ordinary users, authenticated nonmembers, group members/nonmembers, each technical role, human-derived credentials and independent integration credentials.

Required positive cases: anonymous creation, ordinary public editing/model work and ordinary fork/archive/export remain as before; ordinary invalidation of stale optional feature caches works; valid group members retain existing resource/scopes; public non-embargoed restricted views work without executing the feature; public Batch exception works; unrelated non-embargoed data beside contrasts stays readable. Existing narrower project-config rules remain intact.

Required denial cases: unentitled restricted direct actions and workflow-alias mutations cause no protected state/job changes; generic query/archive/child paths cannot expose embargoed data; nonmember Root cannot execute group-only OpenET/Batch; removed memberships lose new restricted admission even with old user/session/delegated-service credentials; numeric service subjects cannot manufacture human identity. Normal signature/audience/expiry/revocation checks remain enforced, including the observed expired Culvert token.

Implementation lead: the current open-mode polling helper returns no principal even when a bearer token is present. Resolve optional verified identity for protected-result entitlement without requiring authentication for ordinary open polling.

Required polling cases: synthetic PATH-CE/contrast results in GET single and POST batch job-info, recursive children and mixed trees; entitled callers retain results, unentitled callers receive `result: null` for wholly protected payloads or an explicit non-protected projection. Check auxiliary metadata/description/error leaks and unchanged lifecycle/queue/ordinary Culvert responses under open polling. Canonical owners are `docs/schemas/rq-response-contract.md` and `wepppy/query_engine/README.md` for job delivery and web/MCP query delivery respectively.

Persistence and runtime acceptance belong to later milestones: real transaction rollback/history retention, current membership freshness, direct safety-boundary tests, accessible browser behavior and actual generated artifacts. No runtime tests or successful live submission were performed during this documentation milestone.

## Review and checkpoint status

Earlier prepared-plan and bounded-source review findings were fixed and independently confirmed. Their obsolete creator/writer recommendations are superseded by the operator's clarification above; they do not authorize broader anonymous changes. Final independent correctness/security reviews passed with no unresolved High/Medium findings; see [disposition](2026-10-01_m0_reviews.md). Record the standalone accepted ancestor in the tracker before runtime work. Credential renewal and positive live Culvert acceptance remain explicit later-stage dependencies, not silently satisfied by documentation or signature-only verification.
