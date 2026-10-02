# Private-resource containment security review

## Metadata

- Package: `docs/work-packages/20261001_feature_access_governance/`.
- Reviewer: `/root/private_boundary_review`, independent security reviewer,
  2026-10-02 UTC.
- Base: committed FA-02 reconciliation `5d4f199e6`; reviewed the uncommitted
  private-resource remediation snapshot.
- Scope: M3-S04 query-engine catalog-source isolation and M3-S08 D-Tale
  public/private viewer admission. This review did not modify runtime code.
- Authority: [feature-access governance contract](../../../schemas/feature-access-governance-contract.md),
  [active plan](../prompts/active/feature_access_governance_execplan.md), and
  [historical M3 security review](2026-10-02_m3_security_review.md).

## Findings

Line references identify the reviewed snapshot and may move as the changes are
committed.

| ID | Severity | Surface | Exploit path and evidence | Required remediation | Status |
| --- | --- | --- | --- | --- | --- |
| M3-S04 | High | Query execution and filesystem containment | Caller-controlled SQL expressions previously executed with DuckDB external file access, so declared-dataset admission did not constrain the effective source set. The remediation resolves catalog paths into `QuerySource` objects (`query_engine/core.py:151-193`), registers only those Arrow sources, rejects dynamic SQL and `ST_Transform`, and disables extension auto-loading and external access before caller SQL executes (`query_engine/executor.py:89-125`). The real DuckDB regression preserves ordinary and spatial queries while denying an undeclared Parquet read (`tests/query_engine/test_core.py:460-583`). | Bind admitted catalog sources before disabling external access; retain the spatial WKB adapter and the documented external-file exclusions. | **Resolved** |
| M3-S08 | High | Cached D-Tale private data | A successful private load previously left its predictable cached dataset available through downstream D-Tale routes without caller admission. Trusted browse now labels each load with current resource visibility and passes verified claims only for private loads (`microservices/browse/dtale.py:248-268`). D-Tale requires a signed short-lived launch ticket and scoped HttpOnly cookie (`webservices/dtale/dtale.py:1473-1509`), filters global lookup/enumeration, propagates scopes to derivatives, gates retained GeoJSON overlays, and reauthorizes every private scope against current token and live run/feature access (`webservices/dtale/dtale.py:239-301,303-418,1113-1181`). Public-to-private changes fail closed. | Preserve anonymous public datasets while enforcing per-viewer live authorization on every private downstream representation and derivative. | **Resolved** |
| PRS-01 | Medium | Session/JWT revocation | During review, `require_current_claims` returned after checking session revocation and skipped the standard JWT `jti` revocation for session tokens. A session capability could therefore outlive explicit token revocation until its own expiry. The final helper always checks numeric expiry and JWT `jti`, then additionally checks session revocation (`rq_engine/auth.py:290-298`). The focused unit test asserts both checks for session credentials (`tests/microservices/test_rq_engine_auth.py:450-469`). | Apply both revocation mechanisms to session credentials before live resource reauthorization. | **Resolved during review** |
| PRS-02 | High | Shared cached GeoJSON key | During review, overlay visibility allowed lookup when any associated dataset was public or authorized. Overlay keys use a shared run/slug namespace, so a public table associated with the same key as an unauthorized private table could make the retained private overlay anonymously readable. The final lookup requires every associated nonpublic dataset to be visible (`webservices/dtale/dtale.py:1113-1148`). The regression confirms the shared key stays hidden until the private capability is present (`tests/microservices/test_dtale_freshness.py:94-127`). | Require authorization for every private dataset associated with a GeoJSON key; do not let a public association relax another association's boundary. | **Resolved during review** |
| PRS-03 | High | Private viewer GeoJSON uploads | During review, viewer-uploaded GeoJSON initially had no private scope. After scope tagging was added, upstream duplicate-key detection still used the filtered lookup: viewer B could reuse viewer A's hidden filename, overwrite its scope provenance, and receive the first raw-registry record under that key. The final upload path records all live private viewer scopes and allocates keys against the unfiltered registry (`webservices/dtale/dtale.py:1150-1181`); cleanup removes the scope provenance (`webservices/dtale/dtale.py:644-688`). The regression gives two viewers distinct keys for the same filename and proves cross-viewer lookup denial (`tests/microservices/test_dtale_freshness.py:130-192`). | Bind uploads to the viewer's live private scope, allocate globally unique raw-registry keys, and remove scope provenance with the overlay. | **Resolved during review** |
| PRS-04 | High | Multi-scope overlay cleanup | A final correctness review found that cleaning one required scope from an uploaded overlay previously removed only that scope from its provenance. An overlay created while capabilities A and B were both live could then change from requiring A and B to requiring only B, disclosing content to a B-only viewer after A was cleaned. Cleanup now deletes an overlay when any required scope is removed, preserving the original conjunction by failing closed (`webservices/dtale/dtale.py:674-688`). The regression removes A from an overlay scoped to `{A, B}` and verifies both provenance and lookup disappear (`tests/microservices/test_dtale_freshness.py:183-190`). | Never weaken a multi-scope overlay's authorization conjunction during cleanup; discard the overlay when any required scope is removed. | **Resolved before final sign-off** |

No unresolved High, Medium, or Low finding remains in this bounded review.

## Security Triage Decision

- **Security impact level**: high.
- **Dedicated security review required**: yes.
- **Triage rationale**: the changes constrain SQL file access and add
  authentication and authorization to a previously public cache-delivery
  surface. A regression could disclose private run or grouped-resource data.
- **Threat model assumptions**:
  - Query expressions, dataset identifiers, D-Tale route parameters, stale
    browser cookies, and known cached dataset IDs are untrusted.
  - The browse service and D-Tale internal loader share the existing protected
    `DTALE_INTERNAL_TOKEN`; callers cannot directly supply trusted decoded claims.
  - Resource visibility, run ownership, group membership, JWT revocation, and
    session revocation can change after a viewer is launched.
  - D-Tale retains its declared one-worker deployment topology. A service
    restart invalidates in-memory private capabilities and fails closed.
- **Valid states that controls must preserve**: ordinary catalog Parquet joins,
  spatial reads through the WKB adapter, anonymous public D-Tale reads,
  authorized private reads, multiple independent authorized viewers, source
  refresh, public-to-private transition, private-to-public reopen, and absent or
  expired capability state.

## Verdict

- **Gate status**: **pass** for the bounded S04/S08 private-resource gate.
- **Unresolved findings**:
  - High: 0.
  - Medium: 0.
  - Low: 0.
- **Release recommendation**: accept the S04/S08 remediations into the broader
  M3 acceptance process. Full package regression, live browser/service checks,
  production-identity parity, and deployment approval remain separate gates.

## Surface Checks

### 0) Valid-State Non-Interference and User Experience

- Ordinary Parquet queries, joins, filter behavior, and the real spatial query
  path remain executable. `ST_Transform` is intentionally unavailable because
  PROJ grid lookup can escape DuckDB's external-access boundary.
- Public D-Tale data remains anonymously readable. Private data returns 403 to a
  fresh anonymous client and becomes readable after a valid launch.
- Independent viewer capabilities prevent one viewer's reload or revocation
  from changing another viewer's identity. The regression revokes viewer A
  after viewer B reloads; A is denied and B remains authorized
  (`tests/microservices/test_browse_dtale.py:543-743`).
- A private-to-public transition becomes anonymously available after reopening
  through the canonical browse/load path. Until that reopen, the stale cached
  private scope fails closed.
- Shared overlay keys require access to every private association. Viewer
  uploads inherit live private scopes, and identical filenames receive distinct
  global keys so one viewer cannot select another viewer's hidden record.
- Removing any scope required by a multi-scope uploaded overlay discards the
  overlay instead of weakening its authorization conjunction.

### 1) Auth, Session, and Authorization

- Browse performs the existing run or grouped-resource admission before handing
  a load to D-Tale. Private loads carry a copy of already verified claims; raw
  bearer tokens are not forwarded.
- Each downstream private request checks capability expiry, JWT expiry and
  `jti` revocation, session revocation when applicable, and current run ownership
  or live feature membership. Authorization errors are translated to denial.
- Launch tickets and viewer cookies are signed with separate salts. Cookies are
  HttpOnly, SameSite Lax, path-scoped to D-Tale, and Secure behind HTTPS.
- Public loads are independently rechecked against current run visibility at the
  loader. Cached public data is converted to a private scope when visibility is
  removed.

### 2) Secrets and Credential Handling

- The design reuses the existing `DTALE_INTERNAL_TOKEN`; no new credential,
  mount, plaintext secret, or fallback grant was introduced.
- Private capability records retain decoded claims inside the single D-Tale
  process for at most the configured one-hour viewer lifetime. Tickets and
  cookies carry only an opaque capability identifier and dataset scope.
- Denial logs include dataset scope and the authorization error, not claims,
  bearer tokens, tickets, or cookie values.

### 3) Input Validation and Output Safety

- Query catalog paths continue through the existing root-containment resolver.
  Registered source names are internal identifiers; caller expressions do not
  receive physical file paths.
- The executor parses the final SQL AST before execution and blocks the two
  known mechanisms that could bypass the intended external-file boundary after
  the spatial extension is loaded: dynamic `query` and `ST_Transform`.
- D-Tale validates visibility type and feature identifiers and rejects private
  loads without verified-claims material. Route, form, query, and JSON dataset
  references are checked; global name/key enumeration omits unauthorized data.

### 4) File System and Run-Tree Boundaries

- Only resolved catalog sources are registered in a query connection. DuckDB
  external access and extension auto-loading are disabled before caller SQL.
- Trusted vector files enter through `pyogrio` Arrow/WKB rather than `ST_Read`.
- D-Tale keeps existing run-root and grouped-root path validation. Private
  overlays may remain in its process-global registry so authorized map behavior
  survives, but lookup and list results require the same live capability. A
  public overlay becomes invisible anonymously when its run becomes private.

### 5) Queue, Worker, and Subprocess Surfaces

- This remediation changes no enqueue site, dependency edge, worker input, or
  subprocess call. The RQ graph gate is not applicable.

### 6) Agentic Tooling and MCP Surfaces

- MCP/query entry authorization remains additive to the executor containment.
  The query connection cannot expand its source set through caller expressions.
- No agent permission, tool token, network egress policy, or publication path
  changed in this slice.

### 7) Network and External Integrations

- Browse-to-D-Tale remains the existing internal HTTP call protected by the
  internal token. No new outbound destination or external integration was added.
- The capability store matches the one-worker D-Tale Compose contract
  (`docker/docker-compose.prod.yml:238-269`). Increasing worker count would
  require a shared capability design or sticky routing and a new review.

### 8) CI/CD and Supply Chain

- No dependency or image version changed. The solution uses the installed
  DuckDB/PyArrow/pyogrio stack and does not rely on an unapproved upgrade.
- No workflow, runner permission, package source, or build credential changed.

### 9) Data Integrity, Locking, and Concurrency

- Query connections and registered relations remain request-local.
- Per-viewer server-side capabilities avoid mutable principal identity on shared
  dataset metadata. Capability cleanup runs on issue, expiry, and dataset
  discard; upstream D-Tale cleanup also removes WEPPpy scope state.
- The one-worker D-Tale topology avoids cross-process cache divergence. Restart
  loses capabilities and requires users to reopen private datasets.

### 10) Logging, Monitoring, and Incident Readiness

- Authorization failures are logged with scope context and fail closed. Query
  parser errors retain diagnostic SQL behavior already present in the service.
- Removing a run's public marker immediately denies anonymous cached-table and
  associated GeoJSON access. JWT/session revocation and live membership removal
  deny subsequent private requests without waiting for the viewer cookie TTL.
- Rollback to `5d4f199e6` would reopen S04/S08 and is not a safe containment
  action; service isolation is the appropriate emergency fallback until the
  remediation can be restored.

## Validation Evidence

Automated check executed independently on the final snapshot:

```text
wctl run-pytest tests/microservices/test_rq_engine_auth.py \
  tests/query_engine/test_core.py \
  tests/microservices/test_browse_dtale.py \
  tests/microservices/test_dtale_freshness.py \
  tests/microservices/test_files_routes.py

186 passed, 13 deprecation warnings in 6.74s
```

The run exercised real DuckDB/Arrow query execution and real D-Tale readers with
Flask grid responses on disposable sources. It covered normal queries, a real
spatial join, undeclared external-file denial, public anonymous tables, private
anonymous denial, launch/cookie admission, current-visibility changes,
per-viewer revocation isolation, source refresh, capability-gated overlay
visibility, public/private shared-key isolation, private-upload scope and key
isolation, conjunction-safe multi-scope cleanup, and run/group handoff payloads.
No new attack payload or real user data was created or used.

Manual source review traced:

- catalog path resolution through relation registration and final DuckDB
  settings;
- browse admission through internal load labeling, launch ticket issuance,
  cookie validation, capability lookup, and live reauthorization;
- enumeration/name/derived-dataset mediation and public/private overlay state;
- the production one-worker D-Tale topology and existing secret mount.

`git diff --check` passed after artifact update.

## Residual Risk

- **Accepted residual risks**: none for S04, S08, or PRS-01 through PRS-04.
- **Validation limits**: this review did not run a real reverse proxy/browser,
  production account, Redis failure injection, deployment, or the complete
  Python suite. Those limits constrain the acceptance claim to this bounded
  private-resource gate; they do not leave a reproduced security finding open.
- **Follow-up**: retain the documented one-worker D-Tale topology and include
  private viewer admission in the package's broader service/browser rollout
  evidence.

## Sign-off

- **Security reviewer**: `/root/private_boundary_review`, 2026-10-02 UTC —
  bounded gate **PASSED**.
- **Package owner**: root orchestrator to link this artifact and complete the
  remaining M3 acceptance and rollout gates.

## Artifact Observability Gate

The comparable artifacts are query catalog/result tables and D-Tale cached table
representations. Their test inputs, catalog metadata, registered relations,
failure responses, grid output, and public/private state transitions are visible
through the existing query and D-Tale interfaces under their normal admission.
The focused tests read semantic output and denial responses from the real
consumers. This slice creates no new scientific artifact format, archive member,
or hidden-only project record.

Live reverse-proxy/browser evidence and production-equivalent identity/mount
parity remain broader package gates. This artifact claims independently executed
source and service-test validation of the private-resource boundaries, not
deployment, incident resolution, or complete package closeout.
