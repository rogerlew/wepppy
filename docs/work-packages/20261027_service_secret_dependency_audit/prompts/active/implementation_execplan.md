# Audit shared service secret dependencies

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

Repair the class of missing runtime secrets exposed by ordinary-user browse authorization, not just the reported endpoint. Add durable governance requiring a bounded search across all consumers of a broken assumption. Preserve authorization and deployment identities. Production deployment remains explicitly on hold.

## Progress

- [x] (2026-10-27 UTC) Confirm incident and March worker precedent; start consumer and topology inventory.
- [x] (2026-10-27 UTC) Add failure-class assessment governance and root pointer.
- [x] (2026-10-27 UTC) Inventory all ten Compose files; repair download, D-Tale, legacy MCP query-engine and HPC browse omissions.
- [x] (2026-10-27 UTC) Add deployment binding gate, foreign-context regressions and real local consumer probes; 218 focused tests pass.
- [x] (2026-10-27 UTC) Independent correctness/security review passes after closing all three findings.
- [x] (2026-10-27 UTC) Separate QA passes; segmented broad validation: 11,821 passed, 181 skipped.
- [x] (2026-10-27 UTC) Scoped change set prepared for authorized commit/push; deployment hold retained.

## Surprises & Discoveries

The February secrets migration omitted browse. March commit `9710b762d` repaired workers without repairing browse. Commit `917fa52cf` repaired dev/prod browse; the initial broader search also finds download sharing browse authorization, D-Tale reauthorizing via RQ auth, and a separate HPC Compose definition.

Review found a second boundary: D-Tale has a foreign Flask app context. The shared ownership/identity helpers must select WEPPcloud's context rather than accept any Flask context. Runtime probes are expanded accordingly.

## Decision Log

On 2026-10-27, scope is all repository-owned service/deployment consumers of Flask startup and shared ownership/feature authorization configuration. Do not redesign authentication or mount secrets to services without a demonstrated dependency. Retain unknowns explicitly. User requested governance and comprehensive assessment and patching; earlier commit/push authorization and deployment hold persist.

## Outcomes & Retrospective

Governance, configuration repairs, context fixes and independent reviews are locally validated. Source hashes and precise coverage are retained. Broad validation and separate QA pass; scoped publication is authorized; production is held. No production containers changed. Source validation is not deployment acceptance.

## Context and Orientation

`wepppy/microservices/browse/auth.py` calls RQ authorization; ordinary user ownership lookup in `wepppy/microservices/rq_engine/auth.py` imports Flask through `get_run_owners_lazy`. Flask requires its signing key, password salt, Redis and database configuration. `docker/docker-compose*.yml` determines the actual consumer environment. Shared database-only feature identity paths must be distinguished from Flask consumers. `scripts/deploy-production.sh` is the sole production entry point; `scripts/compose_deploy_contract.py` validates effective topology.

The triggering request was `/weppcloud/runs/mdobre-shattering-jockey/cfg/aria2c.spec` on wepp1 at 2026-10-26 16:31:10 PDT. Its exception was `RuntimeError: SECRET_KEY (or SECRET_KEY_FILE) must be configured`. Browse's required bindings were absent, not malformed. Admin/root bypass does not exercise ordinary ownership lookup.

## Plan of Work

First amend `docs/standards/hardening-lifecycle-standard.md` with a required failure-class inventory and add a concise root AGENTS pointer. Record the user decision and rationale there. Second search direct Flask imports, ownership helpers, shared auth consumers and every Compose variant, recording source/config evidence and dispositions in `artifacts/assessment.md`. Repair only demonstrated missing configuration. Third extend existing deployment validation and tests where useful, and exercise disposable candidate service containers using real imports/database/auth boundaries without exposing secrets or replacing running services. Finish independent reviews and publish scoped changes.

## Concrete Steps

From `/home/workdir/wepppy`, search with `rg` for Flask imports, `get_run_owners_lazy`, `get_user_models`, and shared authorization calls. Inspect every `docker/docker-compose*.yml`, including overrides, plus other deployment manifests. Use `wctl docker compose config` with output consumed by validators rather than printing secret-bearing environment. Use `wctl run-pytest tests/scripts/test_compose_deploy_contract.py` for focused checks, then required broad sanity when executable code changes. Validate docs with `wctl doc-lint --path <file>` and root size with `tools/check_agents_size.sh AGENTS.md`.

## Validation and Acceptance

Every inventoried consumer must be marked confirmed defect, verified unaffected, or unresolved with evidence. Regression checks must fail for removed required bindings, including indirect consumers. Disposable containers must execute the real lazy import and ownership boundary; ordinary owner success and unrelated-user denial must be checked on the delivery workflow. Do not claim production acceptance before an authorized rollout exercises exact host identities/mounts and candidate revision. Production deployment remains held.

## Idempotence and Recovery

No secret values are copied, rotated or logged. Configuration refers to existing secret IDs. Disposable local containers use `--rm --no-deps` and do not publish ports. Any fixture data must be uniquely named and cleaned up. Rollback is reverting this task's specific patches; preserve unrelated dirty work and existing branches.

## Artifacts and Notes

`artifacts/assessment.md` retains coverage, evidence and limitations. `artifacts/security_review.md` and `artifacts/correctness_review.md` retain independent reviews. `tracker.md` records status. Highest current claim: locally validated with independent security/correctness/QA review and segmented broad coverage. Production remains held.

## Interfaces and Dependencies

Reuse Compose secrets, existing Python JSON/YAML tooling, existing `wctl` wrappers and existing auth entry points. No new third-party dependency, privilege, service or fallback behavior.

Revision: initial plan created 2026-10-27 to turn a point fix into a bounded, evidenced failure-class repair.

Revision: review expanded validation to real foreign-Flask contexts and narrowed deployment gating to the selected recreate set, preserving targeted deployments.

Revision: broad validation exposed a browser-cache path typo; checked its peers, corrected dev and dev.hpc definitions, and reran the failed test plus all remaining nodes successfully.
