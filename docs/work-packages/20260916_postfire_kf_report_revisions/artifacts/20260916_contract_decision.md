# Kf and response-curve contract checkpoint

Date: 2026-09-16 UTC. Starting implementation:
`5f98c577a8cc0dfe5cb0be78f40c231a0d0c8a18`.
Status: accepted after independent reviews and disposition; recorded in the
standalone checkpoint commit. Implementation has not begun. Security impact: high.

## Authority, scope and rationale

The owner requested execution of this package on 2026-09-16. This supersedes
scaffold-only restrictions and includes the previously named forest restart and
nervous-mesquite acceptance rerun after implementation. It does not authorize
other existing-run mutations, deployment to other hosts or push.
The source research and canonical amendments below make the next checkpoint
concrete. The owner subsequently instructed completion after the explicit request for
independent agent reviews and checkpoint commit authority. That continuation
authorizes those required steps, implementation, forest restart and the named
end-to-end run; no further permission checkpoint is needed within this scope.

The intended changes replace new M1's RUSLE dependency with traceable fine-earth
Kf, add an equation response curve and clarify rainfall provenance. They are
intentional behavior changes, not conformance fixes. The numerical equations,
coefficients, delineation, M3 source policy and standalone RUSLE stay unchanged.
No source acquisition library, cache, service, queue or new report endpoint.

The proposed Kf product matches original USSOILS polygon KFFACT in 301,379
compared cells from two distinct regions. Original metadata resolves inherited
horizon/component aggregation. The contradictory 2025 conductivity metadata is
retained and interpreted using original-field lineage and numeric parity;
see [source evidence](kf_source_policy.md). This is not an upstream correction.

## Affected current-contract matrix

Paths are repository-relative. Every amendment below is proposed/pending
conformance; approval must resolve any review findings before implementation.

| Current authority | Exact intended delta |
| --- | --- |
| `docs/adrs/ADR-0068-staley-kf-source-replacement.md` | Source selection, inherited weights, metadata interpretation, alignment and display sampling rationale. |
| `wepppy/nodb/mods/postfire_debris_flow/specification.md` | Promote Kf contract; supersede new-M1 POLARIS/RUSLE requirements. |
| `wepppy/nodb/mods/postfire_debris_flow/docs/kf_source.md` | New canonical source/science/preparation/schema/freshness and artifact inventory. |
| `wepppy/nodb/mods/postfire_debris_flow/docs/m1_predictors.md` | New M1 schema 3; preserve local/legacy readers. |
| `wepppy/nodb/mods/postfire_debris_flow/docs/production_m1.md` | Normal Run prepares missing Kf; source-specific old/new freshness. |
| `wepppy/nodb/mods/postfire_debris_flow/docs/production_m3.md` | Explicitly isolate M3 from Kf changes. |
| `wepppy/nodb/mods/postfire_debris_flow/docs/production_m3_runtime.md` | Shared fixed-source transport extension and M1 attempt-owned preparation. |
| `wepppy/nodb/mods/postfire_debris_flow/docs/model_selection.md` | M1 source requirement changes without changing model selection or M3 prerequisites. |
| `wepppy/nodb/mods/postfire_debris_flow/docs/rainfall_results.md` | Additive predictor reader and rainfall context; read-only curve calculations. |
| `docs/ui-docs/contracts/postfire-debris-flow-control-contract.md` | Preparability, source/failure messages and no RUSLE actions for new M1. |
| `docs/ui-docs/contracts/postfire-debris-flow-report-contract.md` | Exact bounded curve payload/sampling, accepted-source labels, provenance/export rules. |
| `wepppy/weppcloud/feature_registry/specification.md` | Postfire enable_dependencies becomes empty; preserve disturbed/role/backend/locale. |
| `wepppy/weppcloud/feature_registry/feature_registry.yaml` | Runtime dependency-list change deferred until after ancestor; specification records intended delta. |

The Kf contract also specifies the additive Redis advisory soil-policy field
and preflight task dispatch; the existing production M1 preflight-completion
contract is amended by its Kf link. No new queue edge is introduced.

Unchanged governing constraints: `docs/schemas/nodb-persistence-concurrency-contract.md`,
`docs/schemas/rq-response-contract.md`, `docs/schemas/weppcloud-csrf-contract.md`,
`docs/ui-docs/controller-contract.md`, `docs/standards/artifact-observability-standard.md`,
and existing terrain/scalar/dNBR scientific contracts. Their lock, authorization,
CSRF, error, presentation, retention and numerical semantics remain mandatory.

## Input and runtime-state matrix

| State/input | Required outcome and proposed evidence |
| --- | --- |
| Optional Kf state absent or never used | GET remains local and usable; Run creates attempt-owned preparation. No NoDb initialization on reads. |
| Empty attempt directory | Incomplete attempt, never accepted; new attempt may proceed without overwriting it. |
| Valid completed preparation | Validate policy, grid, values and hashes before composition; actual Kf common mean equals S. |
| Partial preparation/HTTP failure | Visible diagnostics; explicit failed attempt; previous acceptance unchanged. |
| Source changes between ranges/final HEAD | Reject mixed object; retain request evidence; no acceptance. |
| Project input/eligibility/read-only/model changes | Recheck before and inside final lock; stale worker cannot publish. |
| M1 with no RUSLE directory or jobs | Normal UI/RQ preparation and publication succeed. |
| Disable RUSLE while postfire enabled | Postfire stays checked/visible immediately and after one/two reloads; enabling postfire does not auto-enable RUSLE/POLARIS. |
| New accepted M1 and unrelated RUSLE/POLARIS change | Remains current if actual Kf/M1 dependencies are unchanged. |
| Actual Kf/policy/terrain/SBS/dNBR/climate change | Currentness false or explicit validation error, never silently current. |
| Supported legacy M1 v1/v2 | Original POLARIS source labels/freshness, readable tables and curves, no rewrite. |
| M3 | Existing thickness preparation and schema 2; no Kf prerequisite or network request. |
| Invalid Kf or incompatible units/grid/schema | Explicit error; no Kw/POLARIS/zero fallback. |
| NaN/masked/-0.1 native values | Missing support with coverage; zero common support stays unavailable. |
| Malformed/hostile path, symlink, sidecar or URL | Existing local confinement and fixed-source allowlist reject; no reads outside authority. |
| No accepted report | Existing empty report; no calculation, fetch or mutation. |
| Accepted missing predictors | Curve unavailable with reason; saved sections remain readable. |
| Constant/decreasing response | Preserve scalar semantics and inverse status; never fabricate positive trend or P50. |
| Unsupported/missing historical rainfall provenance | “Not recorded”; calendar date does not imply observed subdaily peaks. |
| Accepted attempt replaced during query/download | 409 assessment_replaced; no mixed curve/table/CSV identity. |
| Archive/restore | All source ranges, partial records, manifests and results remain visible and byte-preserved. |

All expected absent/preparable states above must reach the normal workflow.
Present corruption is exceptional; recovery creates a new attempt and preserves
the prior evidence. Error contracts remain canonical; report messages do not
expose host paths or raw exception details.

## Compatibility and regression plan

Add schema-3 M1 alongside existing v1/v2, never reinterpret them. Keep parquet
schema 1 and meaning; extend manifest context and browser projection additively.
Reopen actual generated event/design/inverse bundles and confirm source/schema
propagation, independent scalar values and saved-mask consistency. Verify failed
replacement and old-artifact hashes. Old application versions may reject v3;
rollback does not promise v3 readability by old code, and must preserve bundles
for a compatible reader rather than relabel or delete them.

Tests must cover input/state matrix behavior rather than literal schema constants.
Required unmocked boundaries: bounded range transport identity/limits, local
filesystem validation, publication/locking, normal browser/download and archive.
Run targeted backend/frontend checks, full pytest sanity, graph check/live job
tree if edges change, and stub gates when public API changes. See ExecPlan for
commands. Prototype checks do not substitute for these implementation gates.

## Live acceptance and review requirements

Use disposable fixtures for generic no-RUSLE and second-basin acceptance. On
forest inspect installed restart mechanics, preserve prior nervous-mesquite
acceptance and protected-input hashes, restart/verify services, and execute a
normal UI/RQ M1 run. Verify source manifest, event/design/inverse artifacts,
curve/numeric equivalent, rainfall labels, exports and reload. Do not rebuild
soils/climate/delineation/RUSLE or delete existing RUSLE artifacts.

Two independent read-only contract reviews must assess this matrix and all
amendments; the author cannot self-approve. Retain reviews and dispositions,
then record their standalone ancestor revision here and in the tracker. Final
correctness, security and dedicated UX reviews plus real generated-output
acceptance are separate implementation-closeout gates.
