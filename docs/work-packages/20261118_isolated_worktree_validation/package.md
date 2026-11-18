# Durable isolated-worktree validation

Status: Complete locally; integration/deployment not performed. Date: 2026-11-18 UTC.

## Problem and scope

The Roads refactor exposed missing ignored assets, native parsers, browser dependencies, stale database schema and source-writing tests only after expensive broad runs. Add a canonical `wctl run-pytest-worktree` entry point with aggregated prerequisite checks before pytest, explicit read-only runtime reuse, candidate-built controller assets, short temporary paths and source-change receipts. Preserve the existing shared-stack commands and checkout guard. Fix the confirmed profile fixture omission; retain unrelated latency and database migration work outside this change.

## Complexity budget

Use existing Compose one-off containers, CLI context, nonce guard, parser provenance validators and controller builder. No new application dependency, service, shared schema mutation or deployment. The test command does not install packages; the canonical wctl installer bootstraps its existing CLI dependencies. Runtime reuse is explicit and source/lock compatibility checked. Preflight failures are errors, never skips or successful test runs.

## Acceptance

A fresh worktree can run focused tests through one supported command. Broad preflight aggregates absent prerequisites before collection, including a stale PostgreSQL schema. Real isolated-container tests exercise candidate source and runtime identities without restarting shared services. Tests that mutate source produce an unsuccessful receipt. Documentation provides repair commands and separates preflight readiness from test success.

Security impact: high (container mounts and command execution); retain a dedicated security review. No scientific parameterization changes or ADR required.

## Execution

[ExecPlan](prompts/completed/implementation_execplan.md), [tracker](tracker.md).

## Outcome

The supported runner and durable prerequisites guide are implemented and exercised
in real one-off containers. Tooling, profile-fixture, browser and native checks
pass. The full repository gate is attempted and correctly stopped before pytest
by the preexisting seven-column PostgreSQL mismatch. This is local tooling
acceptance, not a claim that the broad suite passed. See
[validation](artifacts/validation.md), [correctness review](artifacts/correctness_review.md)
and [security review](artifacts/security_review.md).
