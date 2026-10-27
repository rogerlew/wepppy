# Correctness and User-Experience Review - Shared service secret dependency audit

## Metadata

- Package: `docs/work-packages/20261027_service_secret_dependency_audit/`.
- Reviewer: independent agent `/root/secret_audit_review` (separate correctness assessment from the security artifact).
- Date: 2026-10-27 UTC.
- Scope: scoped Compose repairs, deployment configuration check, shared Flask consumer paths and real candidate probes.
- Baseline: `917fa52cf`; working-tree candidate, unrelated work excluded.
- Contracts: `docs/infrastructure/secrets.md` (file-backed dependencies), `docs/schemas/weppcloud-browse-auth-contract.md` (Endpoint Policy Matrix), `docs/standards/hardening-lifecycle-standard.md` (Failure-Class Assessment), `docker/AGENTS.md` (deployment boundary).
- Related security review: [security_review.md](security_review.md).

## User Outcome

An authorized ordinary user must obtain a browse download specification, archive data, and private D-Tale data without missing Flask or database configuration errors. Legacy MCP identity resolution must work in query-engine. Unauthorized users remain rejected. A configuration repair must not make a bounded CAP-only deployment depend on unrelated services.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Consumer absent from selected topology | Yes | Do not demand unrelated secrets | Validator nonconsumer tests and targeted scope review |
| Required key/salt absent or empty | No | Fail deployment validation before cutover; never mask dependency | Configuration regression tests; independent whitespace negative control |
| Owned populated private project | Yes | Owner succeeds without Admin/Root bypass | Parent candidate probes; independently reproduced and repaired D-Tale real-context failure COR-01 |
| Ordinary unrelated account | No access | Deny 403/false without leaking data | Parent retained candidate probes |
| Legacy MCP subject | Yes when resolvable | Real account lookup succeeds; unknown subject rejects | Query-engine callback tracing and candidate probe |
| Foreign Flask request context | Yes for D-Tale | Use WEPPcloud ORM's registered context, restore caller context | Independent RuntimeError reproduction, then cold real-context lookup and caller restoration passed |
| Existing isolated inline-secret harness | Yes | Preserve intentionally disposable test configuration | Repository topology tests |
| Targeted CAP repair plus unrelated invalid browse config | CAP scope valid | Validate selected deployment scope; do not widen repair | Selected-cutover validation and targeted CAP regression, COR-02 |

## User-Reachable Error Policy

Missing required runtime configuration is exceptional and should be caught before activation. Missing optional services and another service's active Flask context are valid states. Private-run nonowners are expected denials; owner requests must not turn into 500/403 because of lazy initialization. No route-policy or ownership changes are authorized.

## Generated Artifact Evidence Chain

| Stage | Expected semantics | Evidence / limitation |
| --- | --- | --- |
| Request intent | Ordinary owner's spec/archive retrieval | Candidate HTTP request without privileged role claims |
| Persisted state | Existing private run plus actual ownership | Real local database/NoDb read-only fixture |
| Intermediate | Spec content references permitted download paths | Parent probe reads response content, not just status |
| Consumed input | Archive range is exact existing file bytes | Parent probe compares 16 returned bytes with source |
| Execution output | HTTP 200/206 for owner, 403 for unrelated account | Parent retained candidate results; source content assertions reviewed |
| User-facing result | Downloads work in deployed environment | Production not deployed; exact-host verification held |

No persistence writer is changed. The highest supported completion claim is local candidate validation after remaining findings close, not production incident resolution.

## Findings

| ID | Severity | Surface | Description | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| COR-01 | Medium | D-Tale owner authorization | Secret mounts expose a second dependency failure: `get_run_owners_lazy` uses any current Flask app for WEPPcloud ORM queries. D-Tale uses `build_app`, so valid owner reauthorization raises an unregistered-app RuntimeError. Initial capability probe runs without the actual request context and misses this. | Compare app identity; inspect sibling callbacks; add real Flask/SQLAlchemy foreign-context regressions and D-Tale request-context evidence. | Resolved |
| COR-02 | Medium | Targeted deployment | New validation runs over all active services before `--targeted-cap`/`--targeted-web` select recreated services. An unrelated missing binding blocks the authorized narrower repair. | Validate selected recreated services after scope selection and after pull; preserve full deployment coverage. Add targeted-scope regression. | Resolved |
| COR-03 | Low | Binding validation | `get_secret` strips whitespace, while current validator treats whitespace-only inline values as present. Independent call returned no errors for three whitespace-only required secrets. | Normalize binding strings and test whitespace-only configuration. | Resolved |

## Adjacent Context-Selection Assessment

`session_routes._resolve_user_id_from_fs_uniquifier` and `_resolve_roles_for_user_id` are reachable from D-Tale's shared legacy identity adapters and share the incorrect any-app assumption. They belong in the repair. `user_preferences._application_context` is reached from WEPPcloud preferences/presentation and ASGI rq-engine creation/watershed; no current foreign-Flask caller was found. `admin_job_routes._hydrate_submitter_fields` is invoked only by rq-engine ASGI endpoints. `project_rq_delete` is worker deletion/GC with no foreign app context. `weppcloudr` uses the current route app's own configuration, not the shared ORM. These latter cases are not demonstrated defects within the inspected call paths; no speculative blanket edits are required.

## Verdict

Gate: **pass for reviewed implementation/local validation**, zero unresolved high, medium or low findings. Release recommendation: **hold deployment**. Reviewer: `/root/secret_audit_review`, 2026-10-27 UTC.

COR-01 closes with app-identity checks in all three reachable helpers, real Flask/SQLite regressions for no/own/foreign contexts, and independent cold D-Tale validation. The cold check confirmed WEPPcloud was not preimported, performed a real ownership database lookup inside D-Tale's request context, and confirmed D-Tale remained current after return. Parent capability tests additionally verify owner success and unrelated-user denial.

COR-02 closes with guard placement after selected `RECREATED_SERVICES` construction, retaining the existing post-pull re-resolution, plus `test_targeted_cap_does_not_gate_unrelated_browse_configuration`. COR-03 closes with string normalization; an independent negative control returned all three expected errors for whitespace-only required bindings. Added test `test_runtime_contract_rejects_blank_values_and_requires_explicit_scope` independently passed (**1 passed**), also proving omitted CLI scope fails explicitly.

Independent targeted command: `wctl run-pytest tests/microservices/test_shared_flask_context.py tests/scripts/test_compose_deploy_contract.py tests/scripts/test_deploy_production_plan.py -q` — **31 passed**. This review does not replace the broader validation/QA results retained by the parent or exact-host deployment acceptance.

## Artifact Observability Gate

No changed project writer or archive policy. Candidate evidence remains in the package artifact directory; private project files are neither copied nor published. Content verification and environment limitations must remain explicit.
