# Promote project-owned configuration safely to production

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to
date as work proceeds. Maintain it according to
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

This package turns the Forest-accepted project-owned configuration feature into
a production capability. After completion, users can create and reopen
locale-aware projects, run authorized landuse, soil, and climate operations,
and explicitly refresh eligible capability authority on production while
legacy projects continue to work. Operators retain a proven rollback reader
and the shared `_defaults.toml` compatibility alias remains for WP13.

## Progress

- [x] (2026-08-31 16:06 UTC) Verify branch, upstream, merge base, and candidate.
- [x] (2026-08-31 16:06 UTC) Scaffold WP12 governance and active ExecPlan.
- [x] (2026-08-31 16:18 UTC) Repeat amendment 4 and amendment 5 changed-file
  comparisons with no unexplained production/test path.
- [x] (2026-08-31 16:18 UTC) Disposition all later commits and correct six
  historical Markdown EOF-blank-line findings.
- [x] (2026-08-31 17:25 UTC) Run and record complete runtime, frontend,
  stub/hygiene, exception, Vulture, RQ graph, and documentation promotion gates
  with explicit dispositions.
- [x] (2026-08-31 17:35 UTC) Complete final correctness and security promotion
  evidence with no unresolved findings.
- [x] (2026-08-31 17:42 UTC) Commit exact validated pre-merge candidate
  `039192492ffec38782893a603916a2e91918cfca`.
- [ ] Merge the accepted feature revision to `master` and record the revision.
- [ ] Deploy the canonical revision, stage flags, observe health, and verify
  rollback compatibility.
- [ ] Hand revision inventory and evidence to WP13 and close WP12.

## Surprises & Discoveries

- Observation: WP12 had a roadmap entry but no work-package directory.
  Evidence: `docs/work-packages/20260804_project_config_production_cutover`
  was absent at candidate `30b30b3c6`.
- Observation: the candidate is zero commits behind `origin/master`, so no
  synchronization merge is required before promotion.
  Evidence: `git rev-list --left-right --count origin/master...HEAD` returned
  `0 83`.
- Observation: the initial branch-wide diff check reports six historical
  Markdown EOF-blank-line findings.
  Evidence: `git diff --check origin/master...HEAD` names only review artifacts
  in WP09 and the Builder model-options package.
- Observation: final scoped stubtesting found the runtime-exported
  `resolve_preset_locale_projection` absent from the public snapshot stub.
  Evidence: stubtest reported two errors; after adding the exact signature,
  snapshot/update stubtests and 54 direct tests passed.
- Observation: the RQ graph contained the correct 144 edges but one stale
  source line after upload-route expansion.
  Evidence: regeneration changed only `upload_cli_rq` line 145 to 182 and the
  follow-up graph check passed.
- Observation: default test-isolation invocation performs five complete suites
  without actual shuffling when no randomization plugin exists.
  Evidence: the first worker remained active without progress for over four
  minutes; WP12 stopped it and did not claim a pass.
- Observation: the first wepp1 deployment attempt stopped before build because
  `shape-converter` retained the base UID/GID build definition while every
  other `wepppy:latest` service used the wepp1 override definition.
  Evidence: `compose_deploy_contract.py` rejected conflicting build definitions;
  no container was rebuilt or recreated.

## Decision Log

- Decision: Treat WP12 as faithful promotion, not a feature implementation
  package.
  Rationale: All production behavior was implemented and accepted in WP11 and
  WP12B-D; WP12 owns exact-boundary audit, merge, deployment, observation, and
  rollback proof.
  Date/Author: 2026-08-31 / Codex.
- Decision: Retain all rollout ordering and alias constraints from the roadmap.
  Rationale: Reader-before-writer staging and the shared alias are the explicit
  compatibility controls for production and rollback revisions.
  Date/Author: 2026-08-31 / Codex.
- Decision: Use one explicit all-four-flag activation during the limited
  production deployment window instead of a separate reader-only deployment.
  Rationale: On 2026-09-04 the operator explicitly accepted the compressed
  window after the reader, writer, sanitization, Forest, correctness, and
  security gates had passed. Default-off Compose behavior and writer-first
  disablement during rollback remain unchanged.
  Date/Author: 2026-09-04 / Roger Lew and Codex.

## Outcomes & Retrospective

WP12 is in progress. The package and exact candidate are recorded; promotion
remains gated on the repeated scope audits, clean final gates, canonical merge,
and production evidence.

The repeated scope audits passed. Every later commit is either a ratified
WP12D continuation or separately governed, explicitly accepted branch work.
No contract amendment or selective-history release is required.

The pre-merge automated and review gates pass. One additive public-stub defect
and one generated RQ source-line drift were corrected and revalidated. Merge
remains pending the exact final feature checkpoint and final docs/diff rerun.

## Context and Orientation

The initiative branch is `feature/project-owned-config`; `master` is the
canonical production branch. The roadmap at
`docs/schemas/project-owned-config-implementation-roadmap.md` reserves the
first merge and production rollout for WP12. WP11 demonstrated the integrated
stack on Forest. WP12B established locale/view authority, WP12C expanded and
validated the five Builder locales, and WP12D established effective `.cfg`
locale authority and explicit schema-v3 capability refresh.

An accepted boundary means every changed source, test, configuration, and
documentation path is either part of a ratified package or explicitly
dispositioned without hiding a behavioral expansion. Amendment 4's correction
is recorded in
`docs/work-packages/20260827_project_config_run_ui_authority/artifacts/20260828_scope_audit_correction.md`.
Amendment 5 begins at `0ad76c547145bbe323148bac73410ff9cfcd01ef` and has its
own exact source boundary in the WP12D ExecPlan. WP12 must repeat both
comparisons against the final candidate.

Production deployment uses the repository's canonical production deployment
entry point and installed `wctl` preset. Before any production command, inspect
the current deployment script and nearest operator documentation. Record every
deployed and rollback revision; do not infer them from branch names.

## Plan of Work

First create a machine-readable changed-path inventory from the canonical merge
base through the final candidate. Reproduce amendment 4 and amendment 5 ranges,
then classify later paths by their ratified work package or accepted bounded
fix. If any path changes user behavior without documented authority, stop and
ask the operator to accept or exclude it. Repair documentation-only diff-check
findings without changing their meaning.

Next run the complete Python and frontend gates, applicable stub and hygiene
checks, broad-exception enforcement, code-quality observability, documentation
lint, and `git diff --check`. Record exact commands, counts, expected tool debt,
and the final feature revision. Complete a promotion security artifact covering
authentication, authorization, CSRF/session handoff, project mutation, secrets,
deployment inputs, and rollback readers. Reuse but do not overstate prerequisite
review and Forest evidence.

After the exact feature revision is reviewed and pushed, merge it to `master`
without adding unrelated changes. Record the merge revision and push only that
reviewed canonical history. Inspect the canonical deploy script and production
operator guidance, stage all four explicit flags, then deploy the merge revision
once and verify service revisions and health. Exercise authenticated creation
and mutation, legacy reads, project-owned reads, and capability refresh. Observe
logs and queues for the defined health and danger signals.

Finally verify the selected rollback reader can open `_defaults.cfg`, confirm
the shared `_defaults.toml` alias remains, record the deployed and rollback
inventory, synchronize the initiative branch to promoted `master`, and hand
the evidence to WP13. Close WP12 only when all production observations pass.

## Concrete Steps

Work from `/home/workdir/wepppy`.

Record branch state and scopes with:

    git status --short --branch
    git rev-list --left-right --count origin/master...HEAD
    git diff --name-status 596ff5758..588608f1a
    git diff --name-status 0ad76c547..HEAD
    git diff --check origin/master...HEAD

Run canonical gates with:

    wctl run-pytest tests --maxfail=1
    wctl run-npm lint
    wctl run-npm test
    wctl check-test-stubs
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master

Run scoped stub tests and documentation lint selected from the changed-file
inventory. Record any repository-wide tool debt separately from changed-code
failures. Do not classify a failing changed-code gate as pre-existing without
comparison evidence.

Before deployment, read `scripts/deploy-production.sh`, the production operator
instructions, and relevant Docker `AGENTS.md`. Use only the canonical installed
preset and explicit production hosts. Never deploy a branch-only revision as
the WP12 production revision.

## Validation and Acceptance

Acceptance requires a clean, pushed feature candidate; repeated amendment 4
and 5 scope audits with no undispositioned path; complete automated gates or an
evidence-backed disposition of tool-only debt; no unresolved medium/high
security or correctness finding; a recorded merge revision on `master`; and a
production deployment of that exact canonical revision.

Production must show healthy web and RQ services, valid authenticated project
creation/mutation, successful legacy and project-owned reads, expected locale
controls, and no manifest/config inconsistency. Rollback acceptance requires a
recorded reader-compatible revision that opens project-owned `_defaults.cfg`.
The shared `_defaults.toml` alias must remain present.

## Idempotence and Recovery

Audits and tests are read-only and repeatable. Documentation corrections are
small commits on the feature branch. Do not merge while a scope discrepancy is
open. The production deploy must use exact revisions and the documented
rollback mechanism. If activation fails, disable the three writer flags first
while retaining the compatible reader when safe, then investigate or restore
the last known production revision.

## Artifacts and Notes

Store final scope inventory, validation transcript, correctness/security
reviews, deployment evidence, observation notes, and the revision inventory
under this package's `artifacts/` directory. Do not store secrets, tokens, or
sensitive production logs.

## Interfaces and Dependencies

WP12 changes no application interface by design. It depends on the exact
contracts and evidence owned by WP11, WP12B, WP12C, and WP12D, the canonical
deployment script, production Compose configuration, `wctl`, and supported
reader revisions. WP13 consumes the promoted and rollback revision inventory
and retains exclusive authority to remove the shared compatibility alias.

Plan revision note (2026-08-31): Initial WP12 execution plan created from the
roadmap promotion contract after operator authorization.

Plan revision note (2026-08-31 16:18 UTC): Recorded successful amendment 4/5
scope repetition, post-amendment dispositions, and minimal diff-check repair.

Plan revision note (2026-08-31 17:35 UTC): Recorded final validation,
correctness/security review, stub and RQ evidence corrections, and explicit
test-isolation tooling disposition.

Plan revision note (2026-08-31 17:42 UTC): Bound validation and repeated scope
audit to exact pre-merge candidate `039192492ffec38782893a603916a2e91918cfca`.

Plan revision note (2026-09-04): Recorded the operator-approved single-window
activation and missing dedicated-worker Compose passthrough remediation.
