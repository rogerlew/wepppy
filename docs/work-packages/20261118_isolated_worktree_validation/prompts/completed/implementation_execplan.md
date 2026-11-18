# Make isolated-worktree tests repeatable

This living ExecPlan follows docs/prompt_templates/codex_exec_plans.md.

## Purpose / Big Picture

Run candidate tests from an isolated worktree without improvising mount commands or discovering missing assets halfway through a broad suite. A single wctl command prepares candidate controller output, validates explicit runtime inputs, reports all missing prerequisites, and only then starts pytest. A failed preflight must say that no tests ran.

## Progress

- [x] Inspect CLI context, nonce verification, Compose helpers and retained Roads failure evidence.
- [x] Implement runner, preflight, receipts and meaningful regression coverage.
- [x] Exercise real container rejection and successful execution; update durable documentation and reviews.

## Surprises & Discoveries

Worktrees exclude ignored node_modules and generated bundles. The installed image also lacks native parser assets used by broad tests. The live test database can lag model columns. The existing checkout nonce guards source identity but does not establish runtime readiness. Full-suite source integrity can fail through import-time script writes.

## Decision Log

2026-11-18: Add an opt-in command using the installed preset's Compose configuration and explicit candidate checkout, rather than remounting shared services. Default to broad prerequisites; allow explicit narrow profiles for targeted tests. Build controller output from candidate sources; only reuse external dependencies with compatibility evidence. No automatic database migration or dependency installation. Detect source mutation and preserve a failing receipt rather than restoring files silently.

## Outcomes & Retrospective

Implementation complete locally. Tooling, feature-access fixture, browser and native suites pass through the new command. Real broad preflight aggregates missing assets and detects seven absent user columns before pytest. With compatible assets supplied, only the schema prerequisite remains. The broad suite is not claimed green; schema provisioning and catalog latency diagnosis remain outside this package. No shared stack or schema was changed. Reviews are primary-integrator self-reviews, not independent approvals. See artifacts/validation.md for exact logs and receipts.

## Context and Orientation

Host orchestration belongs in tools/wctl2/commands and uses CLIContext plus docker.run_compose. Container checks belong in tools/wctl2/test_runtime.py and reuse shape_converter/parser_provenance.py. The candidate mounts at /workdir/wepppy. Common Git metadata is mounted read-only at its existing absolute path so linked worktree metadata resolves. Tests belong in tools/wctl2/tests. Durable user guidance belongs in wctl/README.md and tools/wctl2/docs, with onboarding pointers in tests/AGENTS.md and wctl/AGENTS.md.

## Plan of Work

M1 adds a one-off runner with explicit candidate, optional dependency checkout and native artifact paths. It never starts dependencies or recreates shared services. M2 adds aggregated browser/native/database preflight, candidate controller generation, fresh receipts and before/after source fingerprints. M3 tests CLI argument/mount safety, missing/stale inputs, actual positive execution and failure before collection, then documents exact commands and open infrastructure requirements.

## Validation and Acceptance

Run the full wctl unit suite through the existing checked container path, then exercise the new command against this live task worktree. Demonstrate that broad preflight rejects the known stale database before pytest and names missing assets together. Demonstrate focused Python and browser/native readiness with existing compatible assets. Verify shared containers are unchanged and source drift causes failure. Run doc lint, broad-exception enforcement and whitespace checks. The root broad test command remains a required attempted gate; a preflight failure is recorded as blocked execution, never a suite pass.

## Idempotence and Recovery

Use unique receipts and short temporary paths. Refuse overwrite of receipts. Only generated ignored candidate assets may be prepared. Runtime mounts are read-only; no secret values are printed. Leave source changes visible if tests mutate files. Roll back by reverting this branch's commits, without resetting shared master or changing the original Roads evidence.

2026-11-18 final discovery: Docker Compose run supports volume flags, not Docker run mount flags; actual invocation caught and corrected this. The task-local canonical shim installation bootstrapped existing declared CLI dependencies without replacing the shared CLI. The interrupted-run regression now requires a persisted running state before starting pytest. Runtime identities and source fingerprints are rechecked after tests; no automatic cleanup conceals drift.
