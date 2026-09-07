# Tracker — Anonymous Project Creation Policy

**Started**: 2026-09-07 20:40 UTC
**Last updated**: 2026-09-07 21:27 UTC
**Phase**: Closed
**Checkpoint ancestor**: `fb67f32fc`
**Security impact**: high; dedicated review required
**Starting revision**: `a64c39f8523ba7efab0e13c4973026700f1d780d`
**Completed plan**: [ExecPlan](prompts/completed/anonymous_project_creation_execplan.md)

## Task Board

- [x] Inspect creation API, interfaces rendering, configuration, Compose, and existing tests.
- [x] Record requested behavior, scope assumption, source inventory, and proposed flag.
- [x] Scaffold package, tracker, active plan, and project-board entry.
- [x] Finalize canonical contract amendments and valid-state/error matrix.
- [x] Complete two independent checkpoint reviews, disposition, and standalone ancestor `fb67f32fc` before code changes.
- [x] Implement policy parsing, API enforcement, and conditional interface rendering.
- [x] Wire both services and update Docker/user/developer documentation.
- [x] Run focused and broad validation and real workflow checks in both flag modes.
- [x] Complete correctness/UX and dedicated security artifacts; close medium/high findings.
- [x] Complete closure documentation and archive the executed prompt.

## Decisions

**2026-09-07 20:40 UTC:** Interpret request as anonymous-only restriction, preserving logged-in/API creation. Proposed `WEPPCLOUD_ALLOW_ANONYMOUS_PROJECT_CREATION=true` preserves default behavior; false opts in. Hide anonymous creation forms and CAPTCHA at render time and enforce independently at the API. Exact behavior and rationale: [package, Behavior and Decision Provenance](package.md#behavior-and-decision-provenance).

**2026-09-07 20:40 UTC:** Scope this turn to scaffolding. Contract ratification, implementation, commits, and deployment are not represented as completed. Separate creation paths require an explicit inventory/disposition before any site-wide claim.

## Risks and Open Items

Cross-service flag drift can advertise unavailable actions or leave an API permissive. Mixed session/CAPTCHA input can reject valid logged-in users if the existing branch order is reused blindly. Fork and other allocators may remain anonymous outside this endpoint. See [inventory](artifacts/change_inventory.md) for mitigation and verification details.

## Validation and Handoff

Scaffold validation: `wctl doc-lint` passed for all four package files and `PROJECT_TRACKER.md` (zero errors/warnings); `git diff --check` passed. Spelling normalization was previewed; suggestions were left unapplied to preserve technical prose and unrelated board history. No production files changed or runtime tests run for this planning-only delivery. Implementation gates and evidence commands are in the active plan. Baseline focused tests: 57 passed, one existing migration-selector test failed by reaching a real Postgres lookup from its unit stub. The implementation phase will isolate that test lookup while preserving selector coverage.

## Final Validation — 2026-09-07 21:27 UTC

Implementation commits: `935d96220`, `43be30d31`; standalone checkpoint `fb67f32fc` precedes both. Focused 296 passed; OpenAPI 12 passed after description-budget fix; full suite **7,721 passed, 72 skipped**. Frontend 108 suites / 835 tests passed; lint, stub completeness, broad-exception enforcement, and scoped docs lint passed.

Real development HTTP/Chromium checks passed in true and false modes, including 16 exact no-allocation snapshots, valid cookie plus stale CAPTCHA, hostile/missing origin, signed session/uppercase tokens, unavailable/conflicting accounts, and service/MCP access. All ten disposable runs/ownership records were removed; both services are restored to true. See `artifacts/20260907_validation.md` and linked JSON evidence. No production rollout occurred.

Confirmed friction: the existing OpenAPI description budget required concise metadata, and NFS log handles required deferred canary cleanup after service recreation. The retained browser canary sanitizes failure messages because Playwright may embed filled credentials in exceptions. No infrastructure or dependency redesign is needed.

**Closure — 2026-09-07 21:27 UTC:** independent correctness/UX and security gates passed, with zero unresolved findings. Package owner accepts final evidence; implementation scope is complete. Durable decisions live in `docs/schemas/project-creation-policy.md` (Configuration, API Authorization, Interfaces, Compatibility and Rationale). Production activation remains optional and was not performed.
