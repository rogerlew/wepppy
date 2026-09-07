# Tracker — Anonymous Project Creation Policy

**Started / last updated**: 2026-09-07 20:40 UTC
**Phase**: Contract checkpoint and independent reviews
**Security impact**: high; dedicated review required
**Starting revision**: `a64c39f8523ba7efab0e13c4973026700f1d780d`
**Active plan**: [ExecPlan](prompts/active/anonymous_project_creation_execplan.md)

## Task Board

- [x] Inspect creation API, interfaces rendering, configuration, Compose, and existing tests.
- [x] Record requested behavior, scope assumption, source inventory, and proposed flag.
- [x] Scaffold package, tracker, active plan, and project-board entry.
- [ ] Finalize canonical contract amendments and valid-state/error matrix.
- [ ] Complete two independent checkpoint reviews, disposition, and required standalone ancestor commit before code changes.
- [ ] Implement policy parsing, API enforcement, and conditional interface rendering.
- [ ] Wire both services and update Docker/user/developer documentation.
- [ ] Run focused and broad validation and real workflow checks in both flag modes.
- [ ] Complete correctness/UX and dedicated security artifacts; close medium/high findings.
- [ ] Complete closure documentation and archive the executed prompt.

## Decisions

**2026-09-07 20:40 UTC:** Interpret request as anonymous-only restriction, preserving logged-in/API creation. Proposed `WEPPCLOUD_ALLOW_ANONYMOUS_PROJECT_CREATION=true` preserves default behavior; false opts in. Hide anonymous creation forms and CAPTCHA at render time and enforce independently at the API. Exact behavior and rationale: [package, Behavior and Decision Provenance](package.md#behavior-and-decision-provenance).

**2026-09-07 20:40 UTC:** Scope this turn to scaffolding. Contract ratification, implementation, commits, and deployment are not represented as completed. Separate creation paths require an explicit inventory/disposition before any site-wide claim.

## Risks and Open Items

Cross-service flag drift can advertise unavailable actions or leave an API permissive. Mixed session/CAPTCHA input can reject valid logged-in users if the existing branch order is reused blindly. Fork and other allocators may remain anonymous outside this endpoint. See [inventory](artifacts/change_inventory.md) for mitigation and verification details.

## Validation and Handoff

Scaffold validation: `wctl doc-lint` passed for all four package files and `PROJECT_TRACKER.md` (zero errors/warnings); `git diff --check` passed. Spelling normalization was previewed; suggestions were left unapplied to preserve technical prose and unrelated board history. No production files changed or runtime tests run for this planning-only delivery. Implementation gates and evidence commands are in the active plan. Baseline focused tests: 57 passed, one existing migration-selector test failed by reaching a real Postgres lookup from its unit stub. The implementation phase will isolate that test lookup while preserving selector coverage.
