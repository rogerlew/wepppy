# Migrate CI checks off the unavailable homelab runner

This living ExecPlan follows docs/prompt_templates/codex_exec_plans.md.

## Purpose / Big Picture

Useful CI checks must actually execute on registered runners instead of queuing
forever. Preserve checks and reports while removing Forest host dependencies.
Retire the 21 profile schedules explicitly approved by the operator.

## Progress

- [x] (2026-11-18 UTC) Audit and scope approval retained.
- [ ] M1: Define per-workflow isolated runtime and implement faithful migration.
- [ ] M2: Generate YAML, validate real commands/reports, inspect security boundaries.
- [ ] M3: Merge approved PR, observe runner execution and clean stale queue entries.

## Surprises & Discoveries

The previous migration covered stubtest and RQ guards only. The generator still
emits homelab profile jobs; fixing generated YAML alone would be undone.
Status2 smoke consumes development Compose secrets; browser accessibility targets
a retired public Forest URL. Both need real runtime migration rather than relabeling.

## Decision Log

The operator chose to migrate nightly checks and retire old profile schedules on
2026-11-18. Keep profile source tools and recorded run history. Use existing owned
CI runtime components; no new host credentials, runners or deployment topology.

## Outcomes & Retrospective

Pending implementation and acceptance. Do not claim runner acceptance from local
YAML checks alone.

## Context and Orientation

.github/forest_workflows holds generator input; scripts/build_forest_workflows.py
writes .github/workflows and the readme profile table. Standalone jobs explicitly
set forest_bootstrap: false. Existing RQ guard/stubtest specs show checkout, LFS
verification, wctl installation, unique COMPOSE_PROJECT_NAME, isolated Compose
startup and unconditional cleanup. docker/docker-compose.test.yml supplies a
sleeping application container plus disposable Redis/Postgres, with internal
networking and no host ports. Browser tests and Status2 smoke have additional
service/runtime needs. Do not use the shared development stack for those tests.

## Plan of Work

M1 updates the three active check specs, eight nightly specs and Cloc. Inspect
each exact command and preserve its assertion/report behavior. Remove scheduled
profile workflow generation and generated profile jobs, preserving profile tooling.
Update workflow instructions and README. Keep any runtime additions minimal and
scoped to demonstrated consumer needs; document compatibility before edits.

M2 runs the builder --check, relevant workflow contract tests through wctl,
real test commands against job-equivalent isolated containers and direct artifact
readback. Exercise cleanup and ensure source/config/credentials are not borrowed
from Forest. Retain correctness/security review evidence with remaining limits.

M3 pushes a task branch, opens the PR, observes required checks and intended job
execution, obtains exact-revision owner policy approval if protected files change,
and integrates without rewriting accepted history. Freshly verify remote ancestry.
Cancel only queued runs of the migrated/retired workflows once their replacement
is accepted; retain IDs and reasons. Do not cancel unrelated work.

## Concrete Steps

Work from /home/workdir/wepppy-ci-runner-migration on task/ci-runner-migration.
Run python3 scripts/build_forest_workflows.py and the same command with --check.
Use wctl run-pytest --profile python -- tests/tools/test_forest_workflow_bootstrap.py
for generator checks. Select the existing isolated test Compose runtime for real
application checks; each invocation uses an explicit unique project and cleans it.

## Validation and Acceptance

No active workflow targets an unregistered label. Existing tests execute and
report artifacts exist with meaningful content. Three PR checks retain their
paths and assertions; nightly schedules remain except approved profile retirement.
No workflow reads Forest host env/secrets or deletes shared data. Actual supported
runner execution is required before claiming migration complete.

## Idempotence and Recovery

Generator changes are reproducible. Job cleanup owns only its project/resources.
Keep runtime/test artifacts for diagnosis. Revert task commits through normal PR
history if needed; never reset shared master or relabel the image-builder runner.

## Artifacts and Notes

The package artifacts/runner-audit.json is the initial read-only GitHub observation.
Record new validation and remote receipt separately from source they identify.

## Interfaces and Dependencies

Reuse wctl, Docker Compose, existing Node/Playwright/Python/Go tools and GitHub
Actions already used in this repository. Preserve authenticated service boundaries.

Initial plan authored 2026-11-18 after scope approval; milestones will be revised
as real runtime evidence resolves the browser and smoke dependencies.
