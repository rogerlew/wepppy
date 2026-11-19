# CI runner migration

Status: active, 2026-11-18 UTC. Target: faithful migration of existing checks.

## Purpose and scope

Three active PR checks and nine telemetry/nightly workflows target an unavailable
homelab runner. Migrate Artifact Observability, NPM Tests, Shape-Converter Gates,
eight nightly suites and Cloc telemetry onto supported execution environments.
The operator explicitly approved retiring the 21 old Forest profile schedules
and CI Samurai Nightly's legacy nuc1–nuc3 SSH/restart schedule;
retain profile tooling and historical evidence. Retire their queued executions
without touching unrelated CI jobs. Preserve test coverage and artifact semantics.

## Contract and complexity budget

Use the existing remote-ci runner and isolated test Compose runtime where needed.
Keep public PR jobs off the trusted ghcr-builder. No new runner, privilege, host
secret dependency or production deployment. Use job-scoped projects and cleanup;
never delete host Redis data or borrow Forest configuration. Retiring profile
schedules is approved because they depend on obsolete Forest orchestration;
nightly checks remain useful and must migrate rather than silently disappear.

Security impact: high (CI execution boundaries). Dedicated security and correctness
review artifacts required. Implemented, generated, locally tested, runner-tested,
and remotely integrated are distinct claims. Generated YAML and actual test/report
outputs from the new runtime are acceptance evidence, not label changes alone.

## Execution

See [ExecPlan](prompts/active/implementation_execplan.md) and [tracker](tracker.md).
