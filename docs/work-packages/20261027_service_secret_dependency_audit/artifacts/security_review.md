# Security Review - Shared service secret dependency audit

## Metadata

- Package: `docs/work-packages/20261027_service_secret_dependency_audit/`.
- Reviewer: independent `security_reviewer` agent `/root/secret_audit_review`.
- Date: 2026-10-27 UTC.
- Scope: consumer-specific Compose secret mounts, deployment binding validator, shared authorization dependency paths, candidate probe and tests.
- Context: working-tree candidate on `master`, baseline `917fa52cf`; unrelated query-catalog work excluded.
- Related artifact: [correctness_review.md](correctness_review.md).

## Security Triage Decision

High impact; dedicated review required because the change adds existing authentication secrets to additional runtime consumers and changes deployment validation. Remote callers remain constrained by the existing JWT, ownership, workflow-group, private-data capability and run-path checks. The operator requested repairs of confirmed dependency omissions; this does not authorize bypasses, rotation, identity changes or new service exposure.

Added mounts are justified by reachable dependencies: browse/download ordinary ownership, D-Tale capability reauthorization, and query-engine legacy MCP identity resolution all reach Flask initialization. Postgres is additionally required by download's real account/ownership lookup. No global shared-image secret grants were introduced. Compromise of one of these consumers would expose the newly mounted key/salt; that is the existing shared-Flask dependency being restored, not justification to redesign authentication in this repair.

Valid states include a private owned populated run, ordinary credentials without privileged roles, an unrelated account, supported legacy MCP identity, absent optional service topology, and existing explicit isolated test credentials. Missing required production bindings are invalid configuration; absent unrelated services are not.

## Findings

| ID | Severity | Surface | Description / evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Valid-state non-interference | D-Tale has its own Flask app. `get_run_owners_lazy` treated any app context as WEPPcloud, so adding secrets alone leaves ordinary-owner authorization denied. Independent disposable D-Tale probe reproduced SQLAlchemy's unregistered-app RuntimeError inside `mod.app.test_request_context`, while the same lookup succeeded outside that context. See COR-01. | Select the WEPPcloud app context explicitly, assess sibling identity helpers, and prove owner acceptance plus unrelated-user denial under the actual D-Tale request context. | Resolved: app identity checks and real request-context evidence |

## Verdict

Gate: **pass for the reviewed implementation**, with zero unresolved high, medium or low security findings. No new authorization bypass, secret-value disclosure or unneeded global mount was found. Release recommendation: **hold deployment** until the operator authorizes it and exact-host acceptance passes; this review does not establish production recovery.

## Surface Checks

Auth/JWT/CSRF policy is not changed by the Compose repair. File-backed mounts refer to existing secret IDs; no credential values appear in diffs or probe output. The candidate probe mints short-lived local credentials in memory without logging them, preserves run ownership checks, and performs read-only project/database operations. No queue wiring, external egress, dependency installation, file-export policy, runtime UID/GID or public route changes are introduced. Deployment JSON is consumed by the validator rather than printed; errors name variables and services, not values.

Configuration validation does not prove file readability, file contents, exact-host identity or user workflow acceptance. The work package must preserve that limitation. Deploy/recovery evidence and rollback belong to the canonical deployment entry point, and deployment is not authorized here.

## Validation Evidence

Independent source review traced ordinary ownership and legacy MCP paths through browse, download, D-Tale, query-engine and shared RQ auth. Review read all deployment overrides and the required secret resolver. Independent read-only reproduction in `wctl docker compose run --rm --no-deps -T dtale python -` on Forest, 2026-10-27 01:34 UTC, produced:

    outside_dtale_context True
    inside_dtale_context RuntimeError The current Flask app is not registered with this 'SQLAlchemy' instance.

The initial capability probe did not enter D-Tale request context and therefore was insufficient. Remediation readback verified identity comparison against WEPPcloud's app in `get_run_owners_lazy` and both session identity/role lookup helpers. Independent cold retest at 2026-10-27 01:39 UTC imported D-Tale first, verified WEPPcloud had not yet been imported, entered the real D-Tale request context, and then ran the ownership lookup:

    weppcloud_cold True
    foreign_context_lookup_passed True
    caller_context_restored True

Independent focused validation: `wctl run-pytest tests/microservices/test_shared_flask_context.py tests/scripts/test_compose_deploy_contract.py tests/scripts/test_deploy_production_plan.py -q` — **31 passed**. The subsequently added whitespace/explicit-scope regression independently passed (**1 passed**). The parent also retained owner-success/unrelated-user-denial capability evidence under D-Tale's request context. Remaining route-level production acceptance is explicit.

## Residual Risk

Exact production/container filesystem permissions, unavailable host-local overrides and external openwepp manifests have not been validated. They remain deployment gates, not accepted evidence of production recovery. Do not claim all authentication failures or all deployment environments are covered.

## Sign-off

Security reviewer: `/root/secret_audit_review`, 2026-10-27 UTC; reviewed fixes and reran the real cold boundary. Package owner: parent agent; deployment hold remains. No risk acceptance requested or recorded.

## Artifact Observability Gate

No project artifact writer, archive content policy or browse visibility change is introduced. Candidate spec/range-download content readback belongs to correctness evidence; no hidden project evidence or new exclusions are introduced.
