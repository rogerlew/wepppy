# Independent QA review: service secret dependency audit

Reviewer: `/root/secret_audit_qa`, 2026-10-27 UTC. Baseline: `917fa52cf`.
This is the separate QA gate required by the hardening lifecycle standard,
performed after the independent correctness and security reviews passed.

## Scope and evidence

Reviewed the staged task changes and this work package. Unrelated query-catalog
changes are excluded. At initial review, independently checked all 12 hashes in
`candidate_sources.json` against both the index and working-tree contents; all
matched. The subsequent fixture refinement and development-only browser-cache
path correction were reviewed separately; final staging must refresh their
manifest hashes. Reviewed the configuration, deploy integration, shared ORM helpers,
new and adjusted tests, consumer probe, retained results, assessment, governance
and operator documentation. No implementation or production changes were made.

The retained focused log reports **218 passed, 13 warnings**. The correctness
review additionally records its independent focused checks and cold D-Tale
request-context reproduction/verification. QA inspected those results and test
design; it did not repeat the broad suite. After the fixture refinement below,
the context/session rerun reports **61 passed, 13 warnings**. The broad run
reached **11,645 passed, 181 skipped**, then stopped because the installed
Playwright configuration could not find its Chromium headless-shell executable.
This fails before browser requests/assertions, outside the changed code. The
parent must retain the final environment/remainder disposition before handoff.
The development Compose correction adds the missing `wepppy` directory to
`PLAYWRIGHT_BROWSERS_PATH`; it does not change production configuration.

## Assessment

| Area | Assessment |
| --- | --- |
| Regression strength | The configuration tests remove bindings, remove mounts, reference undefined secrets, reject empty/whitespace values and require an explicit scope. Seven base topology checks retain disposable inline credentials and database-only/nonconsumer behavior. |
| Runtime boundary | `test_shared_flask_context.py` uses real Flask contexts, SQLAlchemy queries and a persisted role relationship. Only the heavyweight app bootstrap is replaced. No-context, own-context and foreign-request-context cases detect the actual ORM registration defect, preserve nonempty roles and restore the caller context or context absence. The fixture restores its module replacement and database resources. |
| Deployment regressions | Plan tests exercise the real shell entry point and Python validator using a controlled Compose provider. Missing browse configuration fails before a build plan is produced; the same unrelated defect does not block targeted CAP. Validation occurs after scope selection and is repeated by existing post-pull topology resolution. |
| Consumer evidence | Browse checks specification content; download compares returned archive bytes; both verify owner success and existing nonowner rejection. D-Tale enters its real request context. Query-engine exercises the real legacy identity callback. These checks avoid a privileged-role bypass. |
| Failure-class coverage | The matrix follows indirect dependencies, all ten repository Compose files, restricted queues and the newly discovered foreign-context assumption. Source-only, local runtime and unresolved external environments are distinguished. Claims are bounded to the inspected missing-binding/context failure classes. |
| Maintainability | Small, explicit app-identity checks preserve existing query and authorization logic. The validator extends the established deployment-contract module, reports service/key names without values, and introduces no dependency or general fallback. Three local context checks do not justify a new abstraction. |
| Operator usability | The canonical secrets guide names affected services, the executable configuration check and its limits. Targeted repairs keep their scope. The package retains the initial insufficient D-Tale probe alongside the corrected evidence, without presenting the early pass as acceptance. |
| Governance | The durable standard requires a bounded consumer matrix, peer repairs, real consumer validation and explicit unknowns. Root onboarding, the review template and work-package guidance point to it; the rule does not depend on this package remaining active. |

## Findings and dispositions

No blocking findings. The primary review's COR-01, COR-02 and COR-03 fixes are
present in the reviewed candidate with matching regressions.

| ID | Severity | Follow-up | Disposition |
| --- | --- | --- | --- |
| QA-01 | Operational maintenance obligation | `scripts/compose_deploy_contract.py` has an explicit consumer inventory. A future renamed/new service or newly lazy Flask caller must update it and `docs/infrastructure/secrets.md`; source topology tests alone cannot discover an unknown dependency. | Accepted bounded design, not an unresolved defect. The operator guide and new failure-class governance explicitly require inventory maintenance. No speculative dependency-discovery framework is needed for this repair. |
| QA-02 | Nonblocking test refinement | Strengthen `tests/microservices/test_shared_flask_context.py` with a representative nonempty role and explicit no-context restoration. | Resolved during QA: the parent added a persisted Role relationship and an assertion that `has_app_context()` remains false. QA reviewed the narrow diff and retained 61-test rerun. No production code changed. |

## Verdict and remaining gates

**PASS for the independent QA gate**, with zero unresolved blocking findings.
The scoped code is maintainable, the regressions target the demonstrated
boundaries, and the documentation does not overstate the retained evidence.

This verdict is not production acceptance. Deployment remains **HOLD**. Before
handoff, record the broad-suite disposition and publish the scoped candidate.
Any later authorized rollout must verify the exact revision, effective host
configuration, identities and secret readability, then exercise ordinary-owner
success and nonowner rejection. Full D-Tale browser/MCP transport behavior,
standalone maintenance environments, external manifests and unavailable host
overrides remain outside the demonstrated local coverage.
